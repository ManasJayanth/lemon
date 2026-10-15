
[@react.component]
let make = (~show) =>
  <div>
    {show ? <b> {React.string("visible")} </b> : React.null}
  </div>;
