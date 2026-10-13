switch (ReactDOM.querySelector("#root")) {
| Some(root) => ReactDOM.Client.render(ReactDOM.Client.createRoot(root), <App />)
| None => failwith("missing #root")
};
