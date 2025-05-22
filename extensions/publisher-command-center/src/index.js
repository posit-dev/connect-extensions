import m from "mithril";

import "bootstrap/dist/js/bootstrap.bundle.min.js";
import "@fortawesome/fontawesome-free/css/all.min.css";

import "../scss/index.scss";


import Home from "./views/Home";
import Edit from "./views/Edit";
import Layout from './views/Layout';
import UnauthorizedView from './components/UnauthorizedView';

const root = document.getElementById("app");

// First ask the server “are we authorized?”
m.request({ method: "GET", url: "api/visitor-auth" })
  .then((res) => {
    if (!res.authorized) {
      // Unauthorized → mount our UnauthorizedView component
      m.mount(root, UnauthorizedView);
    } else {
      // Authorized → wire up routes
      m.route(root, "/contents", {
        "/contents": {
          render: () => m(Layout, m(Home)),
        },
        "/contents/:id": {
          render: (vnode) => m(Layout, m(Edit, vnode.attrs)),
        },
      });
    }
  })
  .catch((err) => {
    console.error("failed to fetch visitor-auth", err);
  });
