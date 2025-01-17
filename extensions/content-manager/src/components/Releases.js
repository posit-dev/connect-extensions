import m from "mithril";

const Releases = {
  view: function (vnode) {
    return m(".mb-3.border-bottom", [
      m(".", [m("h5", "Releases"), m("p", "Under Construction...")]),
    ]);
  },
};

export default Releases;
