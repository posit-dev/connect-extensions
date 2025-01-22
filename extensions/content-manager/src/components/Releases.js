import m from "mithril";

import { format } from "date-fns";

import Releases from "../models/Releases";

const Release = {
  view: function (vnode) {
    return m(".row.my-3", [
      m(".d-flex.align-items-center", [
        m("i.fa-solid.fa-code-commit.me-1"),
        m(".font-monospace", vnode.attrs?.id),
        vnode.attrs?.active
          ? m("i.fa-regular.fa-circle-check.ms-1.text-success")
          : "",
      ]),
      m(
        "small.text-secondary",
        format(vnode.attrs?.created_time, "MMM do, yyyy"),
      ),
    ]);
  },
};

export default {
  error: null,

  oninit: function (vnode) {
    try {
      Releases.load(vnode.attrs.content_id);
    } catch (err) {
      this.error = "Failed to load releases.";
      console.error(err);
    }
  },

  onremove: function () {
    Releases.reset();
  },

  view: function () {
    if (this.error) {
      return m("div", { class: "error" }, this.error);
    }

    const releases = Releases.data;
    if (releases === null) {
      return;
    }

    if (releases.length === 0) {
      return;
    }

    let recent = releases.slice(0, 3);
    recent = recent.map((release) => {
      return m(Release, release);
    });

    let old = releases.slice(3);
    old = old.map((release) => {
      return m(Release, release);
    });
    if (old.length === 0) {
      old = "";
    } else {
      old = [
        m(
          "",
          {
            class: "text-secondary",
            type: "button",
            "data-bs-toggle": "collapse",
            "data-bs-target": "#old",
            onclick: (e) => {
              const icon = e.target.querySelector("i") || e.target;
              const currentRotation =
                icon.style.transform === "rotate(90deg)"
                  ? "rotate(0deg)"
                  : "rotate(90deg)";
              icon.style.transform = currentRotation;
              icon.style.transition = "transform 0.3s ease";
            },
          },
          m("i", { class: "fa-solid fa-ellipsis" }),
        ),
        m("div", { class: "collapse", id: "old" }, old),
      ];
    }

    return m(".pt-3.border-top", [
      m(".", [
        m("h5", [
          "Releases ",
          m("span.badge.rounded-pill.text-bg-secondary", releases.length),
        ]),
        recent,
        old,
      ]),
    ]);
  },
};
