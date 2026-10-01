import m from "mithril";

import ContentsComponent from "../components/ContentsComponent";
import HowItWorks from "../components/HowItWorks";

const Home = {
  view: function () {
    return m(
      "div",
      m("h1", "Content"),
      m(
        "p",
        { class: "text-secondary" },
        "Manage your content and their settings here.",
      ),
      m(HowItWorks),
      m(ContentsComponent),
    );
  },
};

export default Home;
