(* Topologically order OCaml object files and archives for `ocamlc -a`.

   Reads each input with ocamlobjinfo, sorts units by their Requires lists,
   and prints the input files in valid link order (one per line). The OCaml
   toolchain running inside the esy sandbox compiles and runs this; no
   external interpreter is needed. *)
open Printf

let objinfo path =
  let cmd = Printf.sprintf "ocamlobjinfo %s" (Filename.quote path) in
  let ic = Unix.open_process_in cmd in
  let units = ref [] and cur = ref None and reqs = ref [] in
  (try
     while true do
       let line = input_line ic in
       let trimmed = String.trim line in
       if String.length trimmed > 10 &&
          String.sub trimmed 0 10 = "Unit name:" then begin
         (match !cur with Some c -> units := (c, List.rev !reqs) :: !units | None -> ());
         cur := Some (String.trim (String.sub trimmed 10 (String.length trimmed - 10)));
         reqs := []
       end
       else if String.length line > 0 && line.[0] = '\t' && !cur <> None then begin
         (* dependency lines look like (original, untrimmed):
            <TAB><hex-digest><TAB><UnitName> *)
         let name =
           match String.index_opt line '\t' with
           | Some first_tab ->
             (match String.index_from_opt line (first_tab + 1) '\t' with
              | Some second_tab when second_tab + 1 < String.length line ->
                String.trim (String.sub line (second_tab + 1) (String.length line - second_tab - 1))
              | _ -> "")
           | None -> ""
         in
         if name <> "" then reqs := name :: !reqs
       end
     done
   with End_of_file -> ());
   (match !cur with Some c -> units := (c, List.rev !reqs) :: !units | None -> ());
  (match Unix.close_process_in ic with
   | Unix.WEXITED 0 -> ()
   | _ -> prerr_endline ("bundle_order: ocamlobjinfo failed on " ^ path); exit 1);
  List.rev !units

let () =
  let files = Sys.argv |> Array.to_list |> List.tl in
  let unit_file = Hashtbl.create 64 in
  let deps = Hashtbl.create 64 in
  List.iter (fun f ->
      List.iter (fun (u, rs) ->
          if not (Hashtbl.mem unit_file u) then Hashtbl.add unit_file u f;
          Hashtbl.replace deps u rs)
        (objinfo f))
    files;
  (* track insertion order so the sort is deterministic (hash tables are
     not ordered); Python dict ordering is what the original produced *)
  let unit_order = ref [] in
  List.iter (fun f ->
      List.iter (fun (u, _) ->
          if not (List.mem u !unit_order) then unit_order := u :: !unit_order)
        (objinfo f))
    files;
  let unit_order = List.rev !unit_order in
  let order = ref [] and done_ = Hashtbl.create 64 and in_progress = Hashtbl.create 64 in
  let rec visit u =
    if Hashtbl.mem done_ u then ()
    else if Hashtbl.mem in_progress u then ()   (* cycle: impossible in valid inputs *)
    else begin
      Hashtbl.add in_progress u ();
      List.iter (fun d -> if Hashtbl.mem unit_file d then visit d)
        (try Hashtbl.find deps u with Not_found -> []);
      Hashtbl.remove in_progress u;
      Hashtbl.add done_ u ();
      order := u :: !order
    end
  in
  List.iter visit unit_order;
  let emitted = Hashtbl.create 16 in
  List.iter (fun u ->
      match Hashtbl.find_opt unit_file u with
      | Some f when not (Hashtbl.mem emitted f) ->
          Hashtbl.add emitted f ();
          printf "%s\n" f
      | _ -> ())
    (List.rev !order);
  List.iter (fun f ->
      if not (Hashtbl.mem emitted f) then printf "%s\n" f) files
