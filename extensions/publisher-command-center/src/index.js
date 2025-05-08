import m from "mithril";

import "bootstrap/dist/js/bootstrap.bundle.min.js";
import "@fortawesome/fontawesome-free/css/all.min.css";

import "../scss/index.scss";


import Home from "./views/Home";
import Edit from "./views/Edit";
import Layout from './views/Layout'

const root = document.getElementById("app");

// First ask the server “are we authorized?”
m.request({ method: "GET", url: "api/auth-status" })
  .then((res) => {
    if (!res.authorized) {
      // Unauthorized → just show the banner, never mount the router
      m.mount(root, {
        view: () =>
          m(
            "div.alert.alert-info",
            { style: { margin: "1rem" } },
            [
              m("p", [
                "To finish setting up this content, you must add a Visitor API Key ",
                "integration with the Publisher scope."
              ]),
              m("p", [
                'Select "+ Add integration" in the Access settings panel to the ',
                'right, and find an entry with "Authentication type: Visitor API Key".'
              ]),
              m("p", [
                "If no such integration exists, an Administrator must configure one. ",
                "Go to Connect's System page, select the Integrations tab, then ",
                'click "+ Add Integration", choose "Connect API", pick Publisher or ',
                "Administrator under Max Role, and give it a descriptive title."
              ])
            ]
          ),
      });
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
    console.error("failed to fetch auth-status", err);
    // you might also render a generic “uh-oh” banner here
  });
