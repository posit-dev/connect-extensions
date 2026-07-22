import m from "mithril";

import { formatDate, formatRelative } from "../utils/dates";
import { reason } from "../utils/notify";

import Content from "../models/Content";

const About = {
  error: null,

  oninit: function (vnode) {
    Content.load(vnode.attrs.contentId).catch((err) => {
      this.error = `Couldn't load content: ${reason(err)}`;
      console.error(err);
      m.redraw();
    });
  },

  onremove: function () {
    Content.reset();
  },

  view: function (vnode) {
    if (this.error) {
      return m("div", { class: "error" }, this.error);
    }

    const content = Content.data;
    if (content === null) {
      return "";
    }

    const desc = content?.description;
    const updated = content?.last_deployed_time;
    const created = content?.created_time;

    return m(".pt-3.border-top", [
      m(".", [
        m("h5", "About"),
        m("p", desc || m("i", "No Description")),
        m(
          "p",
          m("small.text-body-secondary", "Updated " + formatRelative(updated)),
        ),
        m(
          "p",
          m(
            "small.text-body-secondary",
            "Created on " + formatDate(created, "MMMM do, yyyy"),
          ),
        ),
      ]),
    ]);
  },
};

export default About;
