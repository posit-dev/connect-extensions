import m from "mithril";
import { format } from "date-fns";
import Contents from "../models/Contents";
import Languages from "./Languages";
import LockContentButton from "./LockContentButton";
import DeleteModal from "./DeleteModal";
import RenameModal from "./RenameModal";

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
          m("th", { scope: "col" }, "Title"),
          m("th", { scope: "col" }, "Language"),
          m("th", { scope: "col" }, "Running Processes"),
          m("th", { scope: "col" }, "Last Updated"),
          m("th", { scope: "col" }, "Date Added"),
          m("th", { scope: "col" }, ""),
          m("th", { scope: "col" }, ""),
          m("th", { scope: "col" }, ""),
          m("th", { scope: "col" }, ""),
        ]),
      ),
      m(
        "tbody",
        Contents.data.map((content) => {
          const guid = content["guid"];
          const title = content["title"];
          return m(
            "tr",
            [
              m(
                "td",
                  {
                    class: "link-primary content-page-link",
                    onclick: () => m.route.set(`/contents/${guid}`),
                  },
                  title || m("i", "No Name"),
              ),
              m(
                "td",
                m(Languages, content)
              ),
              m("td", content?.active_jobs?.length),
              m("td", format(content["last_deployed_time"], "MMM do, yyyy")),
              m("td", format(content["created_time"], "MMM do, yyyy")),
              m(
                "td",
                m("button", {
                  class: "action-btn",
                  ariaLabel: `Rename ${title}`,
                  title: `Rename ${title}`,
                  "data-bs-toggle": "modal",
                  "data-bs-target": `#renameModal-${guid}`,
                }, [
                  m("i", { class: "fa-solid fa-pencil" })
                ]),
              ),
              m(
                "td",
                m(LockContentButton, {
                  contentId: guid,
                  contentTitle: title,
                  isLocked: content["locked"],
                }),
              ),
              m(
                "td",
                m("button", {
                  class: "action-btn",
                  title: `Delete ${title}`,
                  ariaLabel: `Delete ${title}`,
                  "data-bs-toggle": "modal",
                  "data-bs-target": `#deleteModal-${guid}`,
                }, [
                  m("i", { class: "fa-solid fa-trash" })
                ]),
              ),
              m(
                "td",
                m("a", {
                  class: "fa-solid fa-arrow-up-right-from-square",
                  href: content["content_url"],
                  ariaLabel: `Open ${title} (opens in new tab)`,
                  title: `Open ${title}`,
                  target: "_blank",
                  onclick: (e) => e.stopPropagation(),
                }),
              ),
              m(DeleteModal, {
                contentId: guid,
                contentTitle: title,
              }),
              m(RenameModal, {
                contentId: guid,
                contentTitle: title,
              }),
            ],
          );
        }),
      ),
    )
  },
};

export default ContentsComponent;
