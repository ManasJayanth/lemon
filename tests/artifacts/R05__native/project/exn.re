
exception Boom(string);
let () =
  try (raise(Boom("caught"))) {
  | Boom(msg) => print_endline("caught: " ++ msg)
  };
