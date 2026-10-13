[@react.component]
let make = (~label) => {
  let (count, setCount) = React.useState(() => 0);
  <div className="counter">
    <h2> {React.string(label)} </h2>
    <button className="value" onClick={_ => setCount(n => n + 1)}>
      {React.string("Clicked " ++ string_of_int(count) ++ " times")}
    </button>
    {count > 0 ? <p className="hint"> {React.string("now positive")} </p> : React.null}
  </div>;
};
