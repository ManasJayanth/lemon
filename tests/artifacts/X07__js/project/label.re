
[@react.component]
let make = (~suffix=?, ()) =>
  <span> {React.string("text" ++ (switch (suffix) { | None => "" | Some(s) => s }))} </span>;
