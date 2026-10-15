
type color = Red | Green | Blue;
exception TooBig;
let describe = c =>
  switch (c) {
  | Red => "red"
  | Green => "green"
  | Blue => "blue"
  };
let safeDouble = n =>
  if (n > 100) { raise(TooBig); } else { n * 2 };
let () = {
  print_endline(describe(Red));
  print_endline(describe(Blue));
  print_int(safeDouble(21));
  print_newline();
  print_int(List.fold_left((a, b) => a + b, 0, [1, 2, 3, 4]));
  print_newline();
  print_endline(string_of_int(int_of_string("7")));
  print_int(String.length("héllo"));  // UTF-16 code units under JS
  print_newline();
  (try (ignore(safeDouble(1000))) {
   | TooBig => print_endline("caught TooBig")
   });
};
