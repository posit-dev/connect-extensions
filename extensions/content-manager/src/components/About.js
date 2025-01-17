import m from "mithril";

import { format, formatDistanceToNow } from "date-fns";

import Content from "../models/Content";

const About = {
  error: null,

  oninit: function (vnode) {
    try {
      Content.load(vnode.attrs.content_id);
    } catch (err) {
      this.error = "Failed to load author.";
      console.error(err);
    }
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

    return m(".mb-3.border-bottom", [
      m(".", [
        m("h5", "About"),
        m("p", desc || m("i", "No Description")),
        m(
          "p",
          m(
            "small.text-body-secondary",
            "Updated " + formatDistanceToNow(updated, { addSuffix: true }),
          ),
        ),
        m(
          "p",
          m(
            "small.text-body-secondary",
            "Created on " + format(created, "MMMM do, yyyy"),
          ),
        ),
      ]),
    ]);
  },
};

export default About;
