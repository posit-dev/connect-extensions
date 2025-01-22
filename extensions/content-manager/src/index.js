import m from "mithril";

import "bootstrap/dist/css/bootstrap.min.css";
import "./index.scss";

import "bootstrap/dist/js/bootstrap.bundle.min.js";

import Home from "./views/Home";
import Edit from "./views/Edit";
import Layout from './views/Layout'

const root = document.getElementById("app");
m.route(root, "/contents", {
  "/contents": {
    render: function () {
      return m(Layout, m(Home))
    },
  },
  "/contents/:id": {
    render: function (vnode) {
      return m(Layout, m(Edit, vnode.attrs));
    },
  },
});
