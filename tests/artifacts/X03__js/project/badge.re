
[@react.component]
let make = (~label, ~count) =>
  <div className=label> <em> {React.string(label)} </em> <strong> {React.string(string_of_int(count))} </strong> </div>;
