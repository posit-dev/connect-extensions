import m from "mithril";

export default {
  view: (vnode) => {
    return m("div", [
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
