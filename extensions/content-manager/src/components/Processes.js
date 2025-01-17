import m from "mithril";

import Processes from "../models/Processes";
import Process from "../models/Process";

import ProcessCard from "./ProcessCard";

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

  view: function (vnode) {
    if (this.error) {
      return m("div", { class: "error" }, this.error);
    }

    const processes = Processes.data;
    if (processes === null) {
      return;
    }

    if (processes.length === 0) {
      return;
    }

    return m(".mb-3", [
      m("h3", "Processes"),
      m(
        ".row",
        Processes.data.map((process) => {
          return m(
            ".col-4",
            m(ProcessCard, {
              id: process.job_key,
              content_id: process.app_guid,
              title: process?.pid,
              cpus: process?.cpu_current,
              mem: process?.ram,
              hostname: process?.hostname,
              started: process?.start_time,
              ondestroy: async function () {
                await Process.destroy(process.app_guid, process.job_key);
                Processes.load(vnode.attrs.id); // Reload the list
                m.redraw(); // Force a UI update
              },
            }),
          );
        }),
      ),
    ]);
  },
};
