
let () = {
  print_endline(ReactDOMServer.renderToStaticMarkup(<Label />));
  print_endline(ReactDOMServer.renderToStaticMarkup(<Label suffix="!" />));
};
