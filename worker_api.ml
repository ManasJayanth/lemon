type request = { source : string; prefix : string; includes : string list }
type worker = {
  dependencies : string -> (string list, string) result;
  (* Parse a Reason (or OCaml) source and write a normalized binary AST file
     with conventional .ml/.mli naming at the given target path. Locations in
     the AST reference the original source, so diagnostics point at it.
     OCaml sources are handled by the caller and never reach this call. *)
  normalize : source:string -> target:string -> (string, string) result;
  compile : request -> (string, string) result;
  link : string list -> string -> (string, string) result;
}

type js_request = {
  source : string;          (* original .ml/.re/.mli/.rei path *)
  prefix : string;          (* build-dir prefix; artifacts land as prefix.{cmi,cmj,js} *)
  includes : string list;   (* build dir, for cross-module resolution *)
  jsx : bool;               (* apply the embedded React JSX transform *)
}

type js_worker = {
  js_compile : js_request -> (string, string) result;
}

(* Only these interfaces cross the private compiler boundaries. *)
let pending : worker option ref = ref None
let register worker = pending := Some worker
let take () =
  match !pending with
  | Some worker -> pending := None; worker
  | None -> failwith "Compiler plugin did not register a worker"

let pending_js : js_worker option ref = ref None
let register_js worker = pending_js := Some worker
let take_js () =
  match !pending_js with
  | Some worker -> pending_js := None; worker
  | None -> failwith "Melange plugin did not register a JavaScript worker"
