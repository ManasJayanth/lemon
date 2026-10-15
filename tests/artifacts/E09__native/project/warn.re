let pick = (x: option(int)) => switch (x) { | Some(v) => v };
let () = print_int(pick(Some(2))); print_newline();
