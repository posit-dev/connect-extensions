import m from "mithril";

import Content from "../models/Content";
import About from "../components/About";
import Releases from "../components/Releases";
import Processes from "../components/Processes";
import Author from "../components/Author";

import Languages from "../components/Languages";

const Edit = {
  error: null,

  oninit: function (vnode) {
    try {
      Content.load(vnode.attrs.id);
    } catch (err) {
      this.error = "Failed to load data.";
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

    return m(
      "div",
      m(".d-flex.flex-row.justify-content-between.align-items-center.my-3", [
        m("h2.mb-0", content?.title || m("i", "No Name")),
        m(
          "a.btn.btn-lg.btn-outline-primary.d-flex.align-items-center.justify-content-center.gap-2",
          {
            href: content?.dashboard_url,
            target: "_blank",
          },
          ["Open in Connect", m("i.fa-solid.fa-arrow-up-right-from-square")],
        ),
      ]),
      m(".row", m(".pb-3", m(Languages, content))),
      m(".row.", [
        m(".col-8", [
          m(
            ".pt-3.pb-3.border-top",
            m("iframe", {
              src: content?.content_url,
              width: "100%",
              style: { minHeight: "50vh" },
              frameborder: "0",
              allowfullscreen: true,
              class: "border border-bottom-0 border-light rounded p-1",
            }),
          ),
          m(Processes, { id: vnode.attrs.id }),
        ]),
        m(".col-4", [
          m(About, {
            desc: content?.description,
            updated: content?.last_deployed_time,
            created: content?.created_time,
          }),
          m(Author, {
            content_id: content?.guid,
          }),
          m(Releases, {
            content_id: content?.guid,
          }),
        ]),
      ]),
    );
  },
};

export default Edit;
