
let text = {|<b> & 'quoted' "double"</b>|};
[@react.component]
let make = () => <code> {React.string(text)} </code>;
