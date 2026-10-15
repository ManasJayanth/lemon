
type shape = Circle(float) | Rect(float, float);
type person = {name: string, age: int};
let describe = s =>
  switch (s) {
  | Circle(r) => "circle r=" ++ string_of_float(r)
  | Rect(w, h) => "rect " ++ string_of_float(w) ++ "x" ++ string_of_float(h)
  };
let people = [{name: "ada", age: 36}, {name: "alan", age: 41}];
let nums = [1, 2, 3];
let arr = [|10, 20|];
let pair = (true, "yes");
let () = {
  print_endline(describe(Circle(2.0)));
  print_endline(describe(Rect(3.0, 4.0)));
  print_int(List.fold_left((a, b) => a + b, 0, nums));
  print_newline();
  print_int(arr[0] + arr[1]);
  print_newline();
  print_endline(snd(pair));
  let names = List.map(p => p.name, people);
  List.iter(print_endline, names);
  switch (List.nth(nums, 1)) {
  | 2 => print_endline("second is two")
  | _ => print_endline("second is not two")
  };
};
