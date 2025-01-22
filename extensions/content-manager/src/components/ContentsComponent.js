import m from "mithril";
import { format } from "date-fns";
import Contents from "../models/Contents";

const ContentsComponent = {
  error: null,

  oninit: function () {
    try {
      Contents.load();
    } catch (err) {
      this.error = "Failed to load data.";
      console.error(err);
    }
  },

  view: () => {
    if (this.error) {
      return m("div", { class: "error" }, this.error);
    }

    const contents = Contents.data;
    if (contents === null) {
      return;
    }

    if (contents.length === 0) {
      return "";
    }

    return m(
      "table",
      { class: "table" },
      m(
        "thead",
        m("tr", [
          m("th", { scope: "col" }, ""),
          m("th", { scope: "col" }, "Title"),
          m("th", { scope: "col" }, "Language"),
          m("th", { scope: "col" }, "Running Processes"),
          m("th", { scope: "col" }, "Last Updated"),
          m("th", { scope: "col" }, "Date Added"),
          m("th", { scope: "col" }, ""),
        ]),
      ),
      m(
        "tbody",
        Contents.data.map((content) => {
          const guid = content["guid"];
          const languages = getLanguages(content);
          return m(
            "tr",
            {
              style: { cursor: "pointer" },
              onclick: () => m.route.set(`/contents/${guid}`),
            },
            [
              m(
                "td",
                m("", {
                  class: "fa-solid fa-gear text-secondary",
                }),
              ),
              m(
                "td",
                m(
                  ".link-primary",
                  content["title"] || m("i", "No Name"),
                ),
              ),
              m(
                "td",
                languages.map((language) => {
                  return m(
                    "span",
                    { class: "mx-1 badge text-bg-primary" },
                    language,
                  );
                }),
              ),
              m("td", content?.processes.length),
              m("td", format(content["last_deployed_time"], "MMM do, yyyy")),
              m("td", format(content["created_time"], "MMM do, yyyy")),
              m(
                "td",
                m("a", {
                  class: "fa-solid fa-arrow-up-right-from-square",
                  href: content["content_url"],
                  target: "_blank",
                  onclick: (e) => e.stopPropagation(),
                }),
              ),
            ],
          );
        }),
      ),
    );
  },
};

const getLanguages = (content) => {
  const languages = [];
  if (content["r_version"] != null && content["r_version"] !== "") {
    languages.push("R");
  }
  if (content["py_version"] != null && content["py_version"] !== "") {
    languages.push("Python");
  }
  if (content["quarto_version"] != null && content["quarto_version"] !== "") {
    languages.push("Quarto");
  }
  if (content["content_category"] === "pin") {
    languages.push("Pin");
  }
  return languages.sort();
};

export default ContentsComponent;
