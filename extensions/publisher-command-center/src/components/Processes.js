import m from "mithril";
import { formatRelative } from "../utils/dates";
import { notifyError, reason } from "../utils/notify";
import Processes from "../models/Processes";

const StopButton = {
  oninit(vnode) {
    vnode.state.isHovered = false;
    vnode.state.disabled = false;
  },

  view(vnode) {
    return m(
      "button",
      {
        class: "btn btn-link text-danger p-0",
        disabled: vnode.state.disabled,
        onclick: () => {
          if (vnode.state.disabled) {
            return;
          }

          vnode.state.disabled = true;
          m.redraw();

          Processes.destroy(vnode.attrs.contentId, vnode.attrs.processId).then(
            () => {
              // The stop succeeded; refresh the list. A failed refresh is not a
              // stop failure, so it must not report "Couldn't stop the process".
              Processes.reset();
              Processes.load()
                .catch((err) =>
                  console.error("Failed to reload processes after stop:", err),
                )
                .finally(() => m.redraw());
            },
            (err) => {
              console.error("Failed to stop process:", err);
              vnode.state.disabled = false; // Re-enable button on error
              notifyError(`Couldn't stop the process: ${reason(err)}`);
              m.redraw();
            },
          );
        },
        title: "Stop Process",
        onmouseover: () => {
          vnode.state.isHovered = true;
          m.redraw();
        },
        onmouseout: () => {
          vnode.state.isHovered = false;
          m.redraw();
        },
      },
      m(
        `i.${vnode.state.isHovered ? "fa-solid" : "fa-regular"}.fa-circle-stop`,
        {
          style: "font-size: 1.2rem;",
        },
      ),
    );
  },
};

export default {
  error: null,

  oninit: function (vnode) {
    Processes.load(vnode.attrs.id).catch((err) => {
      this.error = `Couldn't load processes: ${reason(err)}`;
      console.error(err);
      m.redraw();
    });
  },

  onremove: function (vnode) {
    Processes.reset();
  },

  view: function (vnode) {
    if (this.error) {
      return m("div", { class: "error" }, this.error);
    }

    const processes = Processes.data;
    if (processes === null || processes.length === 0) {
      return m(".pt-3.border-top", [
        m("h5", "Processes"),
        m(
          "p.text-dark",
          "There are no server processes running at this time...",
        ),
      ]);
    }

    return m(".pt-3.border-top", [
      m("h5", "Processes"),
      m(
        "table.table",
        m(
          "thead",
          m("tr", [
            m("th", { scope: "col" }, ""),
            m("th", { scope: "col" }, "Id"),
            m("th", { scope: "col" }, "Started"),
            m("th", { scope: "col" }, "Hostname"),
          ]),
        ),
        m(
          "tbody",
          processes.map((process) => {
            return m("tr.align-items-center", [
              m(
                "td.text-center.py-2",
                m(StopButton, {
                  contentId: vnode.attrs.id,
                  processId: process?.key,
                }),
              ),
              m("td", process?.pid),
              m("td", formatRelative(process?.start_time)),
              m("td", process?.hostname),
            ]);
          }),
        ),
      ),
    ]);
  },
};
