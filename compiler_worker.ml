(* Embedded compiler worker: private copy of the stock OCaml compiler
   libraries plus the pinned Reason parser, loaded privately per domain.
   No refmt execution, no -pp, no external PPX processes. *)

(* The reason findlib package is a wrapped library. *)
module Reason_toolchain = Reason.Reason_toolchain
module Reason_syntax_util = Reason.Reason_syntax_util

(* Reason's public API returns the ppxlib wrapper's parsetree, which is
   astlib 5.02-shaped in this solution, while the host compiler libraries
   speak the 5.05 tree. The definition below makes the version relationship
   a compile-time check: it fails to build if pins drift. *)
let _pin : Ppxlib.Parsetree.structure -> Ppxlib_ast__.Versions.OCaml_502.Ast.Parsetree.structure = Fun.id

module To_host =
  Ppxlib_ast.Convert (Ppxlib_ast__.Versions.OCaml_502) (Ppxlib_ast__.Versions.OCaml_505)

let to_host_structure (ast : Ppxlib.Parsetree.structure) : Parsetree.structure =
  let v502 : Ppxlib_ast__.Versions.OCaml_502.Ast.Parsetree.structure = Obj.magic ast in
  Obj.magic (To_host.copy_structure v502)

let to_host_signature (ast : Ppxlib.Parsetree.signature) : Parsetree.signature =
  let v502 : Ppxlib_ast__.Versions.OCaml_502.Ast.Parsetree.signature = Obj.magic ast in
  Obj.magic (To_host.copy_signature v502)

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

(* Reason -> OCaml parsetree, normalized the way refmt feeds the compiler. *)
let reason_implementation source =
  let lexbuf = Reason_toolchain.setup_lexbuf ~use_stdin:false source in
  let ast, _comments = Reason_toolchain.RE.implementation_with_comments lexbuf in
  ast
  |> Reason_syntax_util.(apply_mapper_to_structure remove_stylistic_attrs_mapper)
  |> Reason_syntax_util.(apply_mapper_to_structure backport_letopt_mapper)
  |> to_host_structure

let reason_interface source =
  let lexbuf = Reason_toolchain.setup_lexbuf ~use_stdin:false source in
  let ast, _comments = Reason_toolchain.RE.interface_with_comments lexbuf in
  ast
  |> Reason_syntax_util.(apply_mapper_to_signature remove_stylistic_attrs_mapper)
  |> Reason_syntax_util.(apply_mapper_to_signature backport_letopt_mapper)
  |> to_host_signature

let parse_implementation source =
  if is_reason source then reason_implementation source
  else Pparse.parse_implementation ~tool_name:"lemon" source

let parse_interface source =
  if is_reason source then reason_interface source
  else Pparse.parse_interface ~tool_name:"lemon" source

(* Stock compiler binary-AST format: magic, then marshalled input name,
   then the tree. ocamlc/ocamlopt accept such files named .ml/.mli. *)
let write_normalized target source structure =
  let oc = open_out_bin target in
  Fun.protect ~finally:(fun () -> close_out oc) (fun () ->
    (if Filename.check_suffix target ".mli" then Config.ast_intf_magic_number
     else Config.ast_impl_magic_number)
    |> output_string oc;
    output_value oc source;
    output_value oc structure)

let dependencies source =
  let names = ref [] in
  match protect (fun () ->
    Depend.free_structure_names := Depend.String.Set.empty;
    Depend.pp_deps := [];
    if Filename.check_suffix source ".mli" || Filename.check_suffix source ".rei" then
      Depend.add_signature Depend.String.Map.empty (parse_interface source)
    else
      Depend.add_implementation Depend.String.Map.empty (parse_implementation source);
    names := Depend.String.Set.elements !Depend.free_structure_names)
  with Ok _ -> Ok !names | Error e -> Error e

let normalize ~source ~target =
  protect (fun () ->
    if Filename.check_suffix target ".mli" then
      write_normalized target source (parse_interface source)
    else
      write_normalized target source (parse_implementation source))

let compile (r : Worker_api.request) = protect (fun () ->
  Clflags.include_dirs := r.includes;
  if Filename.check_suffix r.source ".mli" then
    Compile.interface ~source_file:r.source ~output_prefix:r.prefix
  else
    Compile.implementation ~start_from:Clflags.Compiler_pass.Parsing
      ~source_file:r.source ~output_prefix:r.prefix)

let link objects output = protect (fun () ->
  Compmisc.init_path ();
  Bytelink.reset ();
  Symtable.reset ();
  Bytelink.link objects output)

let () = Worker_api.register { dependencies; normalize; compile; link }
