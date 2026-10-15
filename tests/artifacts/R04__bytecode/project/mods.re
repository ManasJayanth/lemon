
module Math = {
  let double = x => x * 2;
  module Inner = {
    let triple = x => x * 3;
  };
};
let () = {
  print_int(Math.double(7));
  print_newline();
  print_int(Math.Inner.triple(7));
  print_newline();
};
