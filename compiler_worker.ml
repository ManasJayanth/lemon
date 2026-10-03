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

let dependencies source =
  let names = ref [] in
  match protect (fun () ->
    Depend.free_structure_names := Depend.String.Set.empty;
    Depend.pp_deps := [];
    if Filename.check_suffix source ".mli" then
      Depend.add_signature Depend.String.Map.empty
        (Pparse.parse_interface ~tool_name:"lemon" source)
    else
      Depend.add_implementation Depend.String.Map.empty
        (Pparse.parse_implementation ~tool_name:"lemon" source);
    names := Depend.String.Set.elements !Depend.free_structure_names)
  with Ok _ -> Ok !names | Error e -> Error e

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

let () = Worker_api.register { dependencies; compile; link }
