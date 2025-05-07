import m from "mithril";

export default {
  oninit: (vnode) => {
    vnode.state.auth = {authorized: true, setupInstructions: ""};
    m.request({
      method: "GET",
      url: "/api/auth-status"
    })
      .then((res) => {
        vnode.state.auth = res;
        m.redraw();
      })
      .catch((err) => {
        console.error("failed to fetch auth-status", err);
      });
  },

  view: (vnode) => {
    const { authorized, setupInstructions } = vnode.state.auth;


    return m("div", [
      // Authorization instructions when missing token on Connect.
      !authorized &&
      m(
        "div.alert.alert-warning",
        { style: { margin: "1rem" } },
        setupInstructions
      ),

      // Navbar Header
      m("nav.navbar.navbar-expand-lg.bg-light", [
        m("div.container-xxl", [
          m(
            "a.navbar-brand",
            {
              style: { cursor: "pointer" },
              onclick: () => m.route.set(`/`),
            },
            "Publisher Command Center",
          ),
          m("ul.navbar-nav.me-auto", [
            m(
              "li.nav-item",
              m(
                "a.nav-link",
                {
                  style: { cursor: "pointer" },
                  onclick: () => m.route.set("/contents"),
                },
                "Content",
              ),
            ),
          ]),
        ]),
      ]),

      // Content Wrapper
      m("div.container-xxl", vnode.children),
    ]);
  },
};
