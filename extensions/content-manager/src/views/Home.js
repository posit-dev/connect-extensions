import m from "mithril";

import ContentsComponent from "../components/ContentsComponent";

const Home = {
  view: function () {
    return m(
      "div",
      { class: "container" },
      m("h1", "Content Manager"),
      m(
        "p",
        { class: "text-secondary" },
        "Manage your content and their settings here.",
      ),
      m(ContentsComponent),
    );
  },
};

export default Home;
