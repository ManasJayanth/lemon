
print_endline(
  ReactDOMServer.renderToStaticMarkup(
    <Annotated width=42 title="the title"> {React.string("kid")} </Annotated>,
  ),
);
