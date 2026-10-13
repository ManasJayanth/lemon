(* Embedded Melange worker: a private copy of the melange compiler driver
   (pinned 7.0.1-55) plus the pinned Reason parser and React JSX transform,
   loaded privately per domain. JavaScript compilation happens fully
   in-process: no melc, refmt, or ppx processes are ever spawned. *)

module Toolchain = Reason.Reason_toolchain
module Reason_config = Reason.Reason_config
module Reason_syntax_util = Reason.Reason_syntax_util

let protect f =
  let buffer = Buffer.create 256 in
  let formatter = Format.formatter_of_buffer buffer in
  Location.reset ();
  Warnings.reset_fatal ();
  Location.formatter_for_warnings := formatter;
  try
    f ();
    Format.pp_print_flush formatter ();
    Ok (Buffer.contents buffer)
  with exn ->
    Location.report_exception formatter exn;
    Format.pp_print_flush formatter ();
    Error (Buffer.contents buffer)

let is_reason file =
  Filename.check_suffix file ".re" || Filename.check_suffix file ".rei"

(* AST version bridges. Reason's public API is astlib-5.02 shaped; ppxlib's
   current version here is 5.05; Melange speaks its own view of the tree.
   The pin definitions make these relationships compile-time checks. *)
let _reason_is_502 :
  Ppxlib.Parsetree.structure -> Ppxlib_ast__.Versions.OCaml_502.Ast.Parsetree.structure =
  Fun.id

module From_502 = Ppxlib_ast.Convert (Ppxlib_ast__.Versions.OCaml_502) (Ppxlib_ast__.Versions.OCaml_505)
module To_502 = Ppxlib_ast.Convert (Ppxlib_ast__.Versions.OCaml_505) (Ppxlib_ast__.Versions.OCaml_502)
module To_melange = Ppxlib_ast.Convert (Ppxlib_ast__.Versions.OCaml_505) (Melangelib.Ast_io.Melange_ast_version)
module From_melange = Ppxlib_ast.Convert (Melangelib.Ast_io.Melange_ast_version) (Ppxlib_ast__.Versions.OCaml_505)

(* Reason parsetree (ppxlib 5.02) -> ppxlib current (5.05). *)
let to_current_structure (ast : Ppxlib.Parsetree.structure) :
  Ppxlib_ast__.Versions.OCaml_505.Ast.Parsetree.structure =
  Obj.magic (From_502.copy_structure (Obj.magic ast))

let to_current_signature (ast : Ppxlib.Parsetree.signature) :
  Ppxlib_ast__.Versions.OCaml_505.Ast.Parsetree.signature =
  Obj.magic (From_502.copy_signature (Obj.magic ast))

(* Apply the registered ppxlib transformations in-process (the React JSX
   transform registers itself when its library is linked in). The ppxlib
   wrapper's parsetree is the reason-facing 5.02 world; JSX therefore runs
   before the 5.02 -> 5.05 conversion, directly on reason output. *)
let jsx_structure (ast : Ppxlib.Parsetree.structure) : Ppxlib.Parsetree.structure =
  Ppxlib.Driver.map_structure ast

let jsx_signature (ast : Ppxlib.Parsetree.signature) : Ppxlib.Parsetree.signature =
  Ppxlib.Driver.map_signature ast

(* ppxlib current (5.05) -> Melange's parsetree view. *)
let to_melange_structure ast =
  Obj.magic (To_melange.copy_structure ast)

let to_melange_signature ast =
  Obj.magic (To_melange.copy_signature ast)

let melange_to_current_structure (ast : Parsetree.structure) =
  let v : Melangelib.Ast_io.Melange_ast_version.Ast.Parsetree.structure = Obj.magic ast in
  From_melange.copy_structure v

let parse_implementation ~jsx source : Parsetree.structure =
  if is_reason source then begin
    Reason_config.recoverable := false;
    let lexbuf = Toolchain.setup_lexbuf ~use_stdin:false source in
    let ast, _comments = Toolchain.RE.implementation_with_comments lexbuf in
    ast
    |> Reason_syntax_util.(apply_mapper_to_structure remove_stylistic_attrs_mapper)
    |> Reason_syntax_util.(apply_mapper_to_structure backport_letopt_mapper)
    |> (fun a -> if jsx then jsx_structure a else a)
    |> to_current_structure
    |> to_melange_structure
  end else begin
    let ast = Melangelib.Pparse_driver.parse_implementation source in
    if jsx then begin
      (* melange -> 5.05 -> 5.02 (the ppxlib wrapper's world, where the
         registered JSX transform lives) -> back. *)
      let v505 = melange_to_current_structure ast in
      let v502 = To_502.copy_structure v505 in
      let v502 : Ppxlib.Parsetree.structure = Obj.magic v502 in
      jsx_structure v502
      |> to_current_structure
      |> to_melange_structure
    end
    else ast
  end

let parse_interface ~jsx source : Parsetree.signature =
  if is_reason source then begin
    Reason_config.recoverable := false;
    let lexbuf = Toolchain.setup_lexbuf ~use_stdin:false source in
    let ast, _comments = Toolchain.RE.interface_with_comments lexbuf in
    ast
    |> Reason_syntax_util.(apply_mapper_to_signature remove_stylistic_attrs_mapper)
    |> Reason_syntax_util.(apply_mapper_to_signature backport_letopt_mapper)
    |> (fun a -> if jsx then jsx_signature a else a)
    |> to_current_signature
    |> to_melange_signature
  end else begin
    let ast = Melangelib.Pparse_driver.parse_interface source in
    if jsx then begin
      let v505 = From_melange.copy_signature (Obj.magic ast) in
      let v502 = To_502.copy_signature v505 in
      let v502 : Ppxlib.Parsetree.signature = Obj.magic v502 in
      jsx_signature v502
      |> to_current_signature
      |> to_melange_signature
    end
    else ast
  end

let () =
  (* Match the stock driver's initialization (jscomp/core/initialization.ml):
   without bs_only the fork's Lambda carries native-only constructs that the
       JS converter deliberately rejects. *)
  Melange_compiler_libs.Config.bs_only := true;
  Clflags.no_std_include := true;
  ignore (Melange_compiler_libs.Warnings.parse_options false
            Melangelib.Melc_warnings.defaults_w);
  ignore (Melange_compiler_libs.Warnings.parse_options true
            Melangelib.Melc_warnings.defaults_warn_error);
  Melangelib.Js_packages_state.set_output_info
    ~suffix:(Melstd.Js_suffix.of_string ".js") Melstd.Module_system.ESM;
  Worker_api.register_js
    { js_compile = fun (r : Worker_api.js_request) ->
        protect (fun () ->
          Clflags.include_dirs := r.includes;
          Clflags.output_name := Some r.prefix;
          if Filename.check_suffix r.source ".mli" || Filename.check_suffix r.source ".rei" then
            Melangelib.Js_implementation.interface
              ~parser:(parse_interface ~jsx:r.jsx)
              Format.err_formatter r.source
          else
            Melangelib.Js_implementation.implementation
              ~parser:(parse_implementation ~jsx:r.jsx)
              Format.err_formatter r.source) }
