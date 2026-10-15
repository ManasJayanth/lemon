
let add = (a, b) => a + b;
let greet = (~name, ~punct="!", ()) => "hi " ++ name ++ punct;
let rec fact = n => n <= 1 ? 1 : n * fact(n - 1);
let () = {
  print_int(add(19, 23));
  print_newline();
  print_endline(greet(~name="reason", ()));
  print_endline(greet(~name="reason", ~punct="?", ()));
  print_int(fact(5));
  print_newline();
};
