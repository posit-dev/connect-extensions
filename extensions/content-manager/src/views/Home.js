import m from "mithril";

import ContentsComponent from "../components/ContentsComponent";

const Home = {
  view: function () {
    return m(
      "div",
      m("h1", "Contents"),
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
