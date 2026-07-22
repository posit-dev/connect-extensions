import m from "mithril";

import { notifications, dismiss } from "../utils/notify";

// Fixed, top-right stack of dismissible error alerts. Reads the shared queue in
// utils/notify so any component can surface a failure without prop-drilling.
export default {
  view: function () {
    if (notifications.length === 0) {
      return null;
    }
    return m(
      ".position-fixed.top-0.end-0.p-3",
      { style: "z-index: 1080; max-width: 420px;" },
      notifications.map((n) =>
        m(
          ".alert.alert-danger.alert-dismissible.shadow-sm.d-flex.align-items-center",
          { role: "alert", key: n.id },
          [
            m("i.fa-solid.fa-triangle-exclamation.me-2"),
            m("span", n.message),
            m("button.btn-close", {
              type: "button",
              ariaLabel: "Dismiss",
              onclick: () => dismiss(n.id),
            }),
          ],
        ),
      ),
    );
  },
};
