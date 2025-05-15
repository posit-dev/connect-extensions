import m from "mithril";

import Content from "../models/Content";

export default {
  view: function () {
    const content = Content.data;
    const accessUrl = content?.dashboard_url ? `${content.dashboard_url}/access` : "#";

    return m(".pt-3.border-top", [
      m(".", [
        m("h5", "Collaborators"),
        m(
          "p",
          m("small.text-body-secondary.align-items-center", [
            m(".fa-solid.fa-user-lock"),
            " ",
            m("a", { href: accessUrl, target: "_blank" }, "See Collaborators and Manage Access"),
          ])
        ),
      ]),
    ]);
  },
};
