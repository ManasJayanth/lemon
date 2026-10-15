(* Post-process bundle_order output for the Melange worker plugin:
   reorder archives by an explicit provider-before-consumer priority (the
   unit toposorter cannot see through cma-internal unit order).

   Reads the ordered file list on stdin, prints it reordered on stdout.
   Priority lists are compiled in; unlisted files keep their relative order
   after the listed ones. *)
open Printf

let priority = [|
  "/compiler-libs/ocamlcommon.cma"; "ocaml_shadow.cma"; "sexplib0.cma";
  "ppx_derivers.cma"; "astlib.cma"; "ppxlib_ast.cma"; "ppxlib_print_diff.cma";
  "stdppx.cma"; "ppxlib_traverse_builtins.cma"; "/ppxlib/ppxlib.cma";
  "menhirLib.cma"; "reason_easy_format.cma"; "reason_omp.cma"; "/reason/reason.cma";
  "js_parser.cma"; "/pp/pp.cma"; "melange_wrapper.cma"; "melstd.cma";
  "melange_compiler_libs.cma"; "melange_ffi.cma";
  "/dune-build-info/build_info.cma";
  "melange_ppx.cma"; "reason_react_ppx.cma";
|]

let rank t =
  let n = String.length t in
  let rec go i =
    if i >= Array.length priority then Array.length priority
    else if String.length t >= String.length priority.(i)
            && String.sub t (n - String.length priority.(i)) (String.length priority.(i))
               = priority.(i)
    then i
    else go (i + 1)
  in
  go 0

let () =
  let toks = ref [] in
  (try
     while true do
       let line = input_line stdin in
       let t = String.trim line in
       if t <> "" then toks := t :: !toks
     done
   with End_of_file -> ());
  let all = List.rev !toks in
  let listed = List.filter (fun t -> rank t < Array.length priority) all in
  let unlisted = List.filter (fun t -> rank t >= Array.length priority) all in
  let sort_by_rank l =
    List.stable_sort (fun a b -> compare (rank a) (rank b)) l
  in
  let sorted = sort_by_rank listed @ unlisted in
  (* the generated build_info data unit must precede its consumer archive *)
  (match List.filter (fun t -> Filename.basename t = "build_info__Build_info_data.cmo") sorted with
   | data :: _ ->
     let rest = List.filter (fun t -> t <> data) sorted in
     let out = ref [] and inserted = ref false in
     List.iter (fun t ->
         if not !inserted && Filename.basename t = "build_info.cma" then begin
           out := t :: data :: !out;
           inserted := true
         end
         else out := t :: !out) rest;
     List.iter (printf "%s\n") (List.rev !out)
   | [] ->
     List.iter (printf "%s\n") sorted)
