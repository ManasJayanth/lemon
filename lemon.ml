let fail message = raise (Failure message)
let unwrap = function Ok value -> value | Error message -> fail message
let report result = let message = unwrap result in if message <> "" then prerr_string message
let module_name source =
  String.capitalize_ascii (Filename.chop_extension (Filename.basename source))
let absolute path = if Filename.is_relative path then Filename.concat (Sys.getcwd ()) path else path
let load_worker plugin =
  Dynlink.loadfile_private plugin;
  Worker_api.take ()

type job = { source : string; name : string; interface : bool; prefix : string;
             mutable deps : string list; mutable compile_source : string }

let process program args log =
  let fd = Unix.openfile log [Unix.O_WRONLY; Unix.O_CREAT; Unix.O_TRUNC] 0o600 in
  let pid = Fun.protect ~finally:(fun () -> Unix.close fd) (fun () ->
    Unix.create_process program (Array.of_list (program :: args)) Unix.stdin fd fd) in
  let _, status = Unix.waitpid [] pid in
  let channel = open_in_bin log in
  let message = Fun.protect ~finally:(fun () -> close_in channel)
    (fun () -> really_input_string channel (in_channel_length channel)) in
  match status with Unix.WEXITED 0 -> Ok message | _ -> Error (program ^ " failed:\n" ^ message)

let main () =
  let target = ref "bytecode" and target_given = ref false in
  let native_given = ref false and out_dir = ref None in
  let jobs = ref (min 4 (Domain.recommended_domain_count ())) in
  let output = ref None and sources = ref [] in
  let args = Array.to_list Sys.argv |> List.tl in
  let args = match args with "build" :: rest -> rest | rest -> rest in
  let args = match args with [source; target_file] when (Filename.check_suffix source ".ml" || Filename.check_suffix source ".re")
      && not (List.exists (fun s -> Filename.check_suffix target_file s) [".ml"; ".mli"; ".re"; ".rei"]) ->
      ["-o"; target_file; source] | _ -> args in
  let supported_targets = ["bytecode"; "native"; "js"] in
  let rec parse = function
    | [] -> ()
    | "--native" :: rest ->
      if !target_given then fail "Conflicting options: --native cannot be combined with --target";
      native_given := true; target := "native"; parse rest
    | "--target" :: value :: rest ->
      if !native_given then fail "Conflicting options: --native cannot be combined with --target";
      if not (List.mem value supported_targets) then
        fail ("Unknown target: " ^ value ^ ". Supported targets: " ^ String.concat ", " supported_targets);
      target := value; target_given := true; parse rest
    | "--out-dir" :: value :: rest -> out_dir := Some (absolute value); parse rest
    | "-j" :: value :: rest ->
      (match int_of_string_opt value with
       | Some n when n >= 1 -> jobs := n; parse rest
       | _ -> fail ("Invalid worker count for -j: " ^ value))
    | "-o" :: value :: rest -> output := Some (absolute value); parse rest
    | arg :: _ when String.starts_with ~prefix:"-" arg -> fail ("Unknown option: " ^ arg)
    | source :: rest -> sources := absolute source :: !sources; parse rest
  in
  parse args;
  let sources = List.rev !sources in
  if sources = [] then
    fail "Usage: lemon.byte build [-j N] [--target bytecode|native|js] [-o OUTPUT | --out-dir DIR] SOURCE...";
  (match !out_dir with
   | Some _ when !target <> "js" ->
     fail "--out-dir applies to the JavaScript target; use -o for executables"
   | _ -> ());
  if !target = "js" then begin
    (match !output with
     | Some _ -> fail "-o names executables; the JavaScript target publishes a directory with --out-dir"
     | None -> ());
    fail "The JavaScript target is not available in this build"
  end;
  let native = !target = "native" in
  let is_implementation path =
    Filename.check_suffix path ".ml" || Filename.check_suffix path ".re" in
  List.iter (fun source ->
    if not (List.exists (fun e -> Filename.check_suffix source e)
               [".ml"; ".mli"; ".re"; ".rei"]) then
      fail ("Unsupported source syntax: " ^ source ^ ". Supported extensions: .ml .mli .re .rei");
    if not (Sys.file_exists source) then fail ("Source does not exist: " ^ source)) sources;
  List.iter (fun source ->
    match List.filter (fun s -> s = source) sources with
    | _ :: _ :: _ -> fail ("Duplicate input path: " ^ source)
    | _ -> ()) sources;
  let output = match !output with Some path -> path | None ->
    let source = List.find_opt is_implementation (List.rev sources) in
    match source with
    | None -> ""    (* checked again after duplicate-module validation *)
    | Some s -> absolute (Filename.chop_extension (Filename.basename s) ^
        if native then (if Sys.win32 then ".exe" else ".native") else ".byte") in
  let plugin = Filename.concat (Filename.dirname (absolute Sys.argv.(0))) "compiler_worker.cma" in
  Dynlink.allow_unsafe_modules true;
  let coordinator = load_worker plugin in
  if not (Sys.file_exists ".lemon") then Unix.mkdir ".lemon" 0o700;
  let rec make_dir n =
    let path = absolute (Printf.sprintf ".lemon/build-%d-%d" (Unix.getpid ()) n) in
    try Unix.mkdir path 0o700; path with Unix.Unix_error (Unix.EEXIST, _, _) -> make_dir (n+1)
  in
  let build_dir = make_dir 0 in
  Fun.protect ~finally:(fun () ->
    Array.iter (fun name -> Sys.remove (Filename.concat build_dir name)) (Sys.readdir build_dir);
    Unix.rmdir build_dir) (fun () ->
  let tasks = List.map (fun source ->
    {source; name = module_name source;
     interface = Filename.check_suffix source ".mli" || Filename.check_suffix source ".rei";
     prefix = Filename.concat build_dir (Filename.chop_extension (Filename.basename source));
     deps = []; compile_source = source}) sources in
  List.iter (fun task ->
    let kind = if task.interface then "interface" else "implementation" in
    let rivals = List.filter (fun t -> t.name = task.name && t.interface = task.interface) tasks in
    match rivals with
    | _ :: _ :: _ ->
      fail (Printf.sprintf "Duplicate module %s: %s %s provided by %s"
              task.name kind task.name
              (String.concat ", " (List.map (fun t -> t.source) rivals)))
    | _ -> ()) tasks;
  if not (List.exists (fun t -> not t.interface) tasks) then
    fail "An implementation is required to build an executable";
  let provider name =
    let matches = List.filter (fun t -> t.name = name) tasks in
    match List.find_opt (fun t -> t.interface) matches with
    | Some t -> Some t | None -> List.find_opt (fun _ -> true) matches in
  List.iter (fun task ->
    let names = unwrap (coordinator.dependencies task.source) in
    task.deps <- List.filter_map (fun name ->
      if name = task.name then None else Option.map (fun t -> t.source) (provider name)) names;
    if not task.interface then match provider task.name with
      | Some t when t.interface -> task.deps <- t.source :: task.deps
      | _ -> ()) tasks;
  (* Reason sources are parsed by the embedded parser and written as
     normalized binary AST files with conventional .ml/.mli names; OCaml
     interfaces are staged alongside so explicit-interface handling and
     diagnostics keep working. The stock pipeline then compiles those, with
     diagnostics pointing at the original sources. *)
  let compile_source task =
    let target = task.prefix ^ (if task.interface then ".mli" else ".ml") in
    report (coordinator.normalize ~source:task.source ~target);
    target in
  List.iter (fun task -> task.compile_source <- compile_source task) tasks;
  let rec order done_sources remaining acc = match remaining with
    | [] -> List.rev acc
    | _ ->
      let ready, blocked = List.partition (fun t -> List.for_all (fun s -> List.mem s done_sources) t.deps) remaining in
      if ready = [] then fail ("Dependency cycle: " ^ String.concat ", " (List.map (fun t -> t.name) blocked));
      order (List.map (fun t -> t.source) ready @ done_sources) blocked (ready :: acc)
  in
  let waves = order [] tasks [] in
  let count = min !jobs (List.length tasks) in
  let workers = if native then [||] else Array.init count (fun _ -> load_worker plugin) in
  let queue = Atomic.make [] and stopped = Atomic.make false in
  let rec take () =
    let before = Atomic.get queue in
    match before with [] -> None | x :: xs ->
      if Atomic.compare_and_set queue before xs then Some x else take () in
  let run index =
    let rec loop () =
      if not (Atomic.get stopped) then match take () with
      | None -> ()
      | Some (task, result) ->
        let r = try
          if native then process "ocamlopt"
            ["-I"; build_dir; "-c"; "-o"; task.prefix ^ (if task.interface then ".cmi" else ".cmx"); task.compile_source]
            (task.prefix ^ ".log")
          else workers.(index).compile {source = task.compile_source; prefix = task.prefix; includes = [build_dir]}
        with exn -> Error (Printexc.to_string exn) in
        result := Some r;
        (match r with Error _ -> Atomic.set stopped true | Ok _ -> ()); loop ()
    in loop () in
  (* Domains persist across dependency waves; only their private compiler copy is used. *)
  let mutex = Mutex.create () and changed = Condition.create () in
  let generation = ref 0 and finished = ref 0 and shutdown = ref false in
  let domains = Array.init count (fun index -> Domain.spawn (fun () ->
    let rec wait previous =
      Mutex.lock mutex;
      while not !shutdown && !generation = previous do Condition.wait changed mutex done;
      let stop = !shutdown and current = !generation in
      Mutex.unlock mutex;
      if not stop then begin
        run index;
        Mutex.lock mutex;
        incr finished;
        Condition.broadcast changed;
        Mutex.unlock mutex;
        wait current
      end
    in wait 0)) in
  Fun.protect ~finally:(fun () ->
    Mutex.lock mutex; shutdown := true; Condition.broadcast changed; Mutex.unlock mutex;
    Array.iter Domain.join domains) (fun () ->
    List.iter (fun wave ->
      let work = List.map (fun t -> t, ref None) wave in
      Mutex.lock mutex;
      Atomic.set queue work; finished := 0; incr generation;
      Condition.broadcast changed;
      while !finished <> count do Condition.wait changed mutex done;
      Mutex.unlock mutex;
      List.iter (fun (_, r) -> match !r with Some result -> report result | None -> ()) work;
      if Atomic.get stopped then fail "Compilation stopped") waves);
  (* Link order follows implementation dependencies, including edges hidden by interfaces. *)
  let implementations = List.filter (fun t -> not t.interface) tasks in
  List.iter (fun t -> t.deps <- List.filter_map (fun name ->
    Option.map (fun d -> d.source) (List.find_opt (fun d -> d.name = name) implementations))
      (unwrap (coordinator.dependencies t.source))) implementations;
  let ordered = List.concat (order [] implementations []) in
  let objects = List.map (fun t -> t.prefix ^ if native then ".cmx" else ".cmo") ordered in
  let temporary = Filename.temp_file ~temp_dir:(Filename.dirname output) ".lemon-" ".out" in
  Fun.protect ~finally:(fun () -> if Sys.file_exists temporary then Sys.remove temporary) (fun () ->
    report (if native then process "ocamlopt" (objects @ ["-o"; temporary]) (Filename.concat build_dir "link.log")
      else coordinator.link objects temporary);
    Sys.rename temporary output);
  Printf.printf "Lemon: built %s (%s, %d workers)\n%!" output (if native then "native" else "bytecode") count)

let () = try main () with exn -> Printf.eprintf "Lemon: %s\n%!" (Printexc.to_string exn); exit 1
