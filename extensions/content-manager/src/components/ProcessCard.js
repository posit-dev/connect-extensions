import m from "mithril";

import Process from "../models/Process";

export default {
  view: function (vnode) {
    return m(".card", { key: vnode.attrs.id }, [
      m(".card-body", [
        m("h6", vnode.attrs?.title),
        m("p", m("small", "Started " + vnode.attrs?.started)),
        m("p", m("small", "CPUs " + vnode.attrs?.cpus)),
        m("p", m("small", "Memory " + vnode.attrs?.mem)),
        m("p", m("small", "Hostname " + vnode.attrs?.hostname)),
        m("button.btn.btn-outline-danger.fa-solid.fa-trash.float-end", {
          onclick: function () {
            vnode.attrs?.ondestroy();
          },
        }),
      ]),
    ]);
  },
};
