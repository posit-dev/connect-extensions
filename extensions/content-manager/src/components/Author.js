import m from "mithril";

import { formatDistanceToNow } from "date-fns";

import Author from "../models/Author";

export default {
  error: null,

  oninit: function (vnode) {
    try {
      Author.load(vnode.attrs.content_id);
    } catch (err) {
      this.error = "Failed to load author.";
      console.error(err);
    }
  },

  onremove: function () {
    Author.reset();
  },

  view: function (vnode) {
    if (this.error) {
      return m("div", { class: "error" }, this.error);
    }

    const author = Author.data;
    if (author === null) {
      return ""
    }

    return m(".mb-3.border-bottom", [
      m(".", [
        m("h5", "Author"),
        m("p", author?.first_name + " " + author?.last_name),
        m(
          "p",
          m("small.text-body-secondary.align-items-center", [
            m(".fa-regular.fa-at"),
            " ",
            author?.username,
          ]),
        ),
        m(
          "p",
          m("small.text-body-secondary.align-items-center", [
            m(".fa-regular.fa-envelope"),
            " ",
            m("a", { href: `mailto:${author?.email}` }, author?.email),
          ]),
        ),
        m(
          "p",
          m("small.text-body-secondary", [
            "Active ",
            formatDistanceToNow(author?.active_time, { addSuffix: true }),
          ]),
        ),
      ]),
    ]);
  },
};
