import m from "mithril";
import Home from "./views/Home";
import Edit from "./views/Edit";

const root = document.getElementById("app");
m.route(root, "/", {
  "/": Home,
  "/edit/:id": {
    render: function (vnode) {
      return m(Edit, vnode.attrs);
    },
  },
});
