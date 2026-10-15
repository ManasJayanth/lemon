
[@react.component]
let make = (~width: int, ~title: string, ~children) =>
  <section className={string_of_int(width) ++ " " ++ title}> children </section>;
