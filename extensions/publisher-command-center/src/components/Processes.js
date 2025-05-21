import m from "mithril";
import { formatDistanceToNow } from "date-fns";
import { filesize } from "filesize";
import Processes from "../models/Processes";
import Process from "../models/Process";

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

          console.log(`Stopping process ${vnode.attrs.process_id}`);
          Processes.destroy(
            vnode.attrs.content_id,
            vnode.attrs.process_id
          )
            .then(() => {
              console.log(`Stopped process ${vnode.attrs.process_id}`);
              Processes.reset();
              return Processes.load();
            })
            .then(() => {
              m.redraw(); // Trigger UI refresh after reload
            })
            .catch((err) => {
              console.error("Failed to reload processes:", err);
              vnode.state.disabled = false; // Re-enable button on error
              m.redraw();
            });
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
        }
      )
    );
  },
};


export default {
  error: null,

  oninit: function (vnode) {
    try {
      Processes.load(vnode.attrs.id);
    } catch (err) {
      this.error = "Failed to load data.";
      console.error(err);
    }
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
        m("p.text-dark", "There are no server processes running at this time...")
      ])
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
                  content_id: vnode.attrs.id,
                  process_id: process?.key,
                }),
              ),
              m("td", process?.pid),
              m(
                "td",
                formatDistanceToNow(process?.start_time, { addSuffix: true }),
              ),
              m("td", process?.hostname),
            ]);
          }),
        ),
      ),
    ]);
  },
};
