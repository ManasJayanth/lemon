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
(* Only this interface crosses the private compiler boundary. *)
let pending : worker option ref = ref None
let register worker = pending := Some worker
let take () =
  match !pending with
  | Some worker -> pending := None; worker
  | None -> failwith "Compiler plugin did not register a worker"
