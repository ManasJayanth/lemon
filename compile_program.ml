(* Compile and link inside this process using OCaml's compiler libraries.
   This program does not spawn ocamlc or another compiler executable. *)
let () =
  if Array.length Sys.argv <> 3 then begin
    Printf.eprintf "Usage: %s SOURCE.ml OUTPUT.byte\n" Sys.argv.(0);
    exit 2
  end;
  let source_file = Sys.argv.(1) in
  let executable = Sys.argv.(2) in
  try
    let output_prefix = Filename.chop_suffix source_file ".ml" in
    Compmisc.read_clflags_from_env ();
    Compile.implementation
      ~start_from:Clflags.Compiler_pass.Parsing
      ~source_file ~output_prefix;
    Compmisc.init_path ();
    Bytelink.link [output_prefix ^ ".cmo"] executable;
    Printf.printf "Compiled %s -> %s using OCaml %s compiler APIs\n%!"
      source_file executable Sys.ocaml_version
  with exn ->
    Location.report_exception Format.err_formatter exn;
    exit 1
