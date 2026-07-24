import m from "mithril";

import * as bootstrap from "bootstrap";
import "@fortawesome/fontawesome-free/css/all.min.css";

import "../scss/index.scss";

import Home from "./views/Home";
import Edit from "./views/Edit";
import Layout from "./views/Layout";
import UnauthorizedView from "./components/UnauthorizedView";
import { reason } from "./utils/notify";

const root = document.getElementById("app");

// First ask the server whether we're authorized.
m.request({ method: "GET", url: "api/visitor-auth" })
  .then((res) => {
    if (!res.authorized) {
      // Unauthorized: mount the UnauthorizedView component.
      m.mount(root, UnauthorizedView);
    } else {
      // Authorized: wire up routes.
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
    // The auth check itself failed (e.g. Connect is unreachable). Show why
    // instead of leaving a blank page.
    console.error("failed to fetch visitor-auth", err);
    m.mount(root, {
      view: () =>
        m(
          ".alert.alert-danger",
          {
            style: {
              margin: "1rem auto",
              maxWidth: "640px",
              width: "calc(100% - 2rem)",
            },
          },
          [
            m("h5", "Couldn't start the app"),
            m("p", reason(err)),
            m("p", "Reload the page to try again."),
          ],
        ),
    });
  });
