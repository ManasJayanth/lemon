
let () = {
  print_endline(ReactDOMServer.renderToStaticMarkup(<App show=true />));
  print_endline(ReactDOMServer.renderToStaticMarkup(<App show=false />));
};
