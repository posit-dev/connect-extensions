import m from "mithril";
import Contents from "../models/Contents";
import { notifyError, reason } from "../utils/notify";

const LockContentButton = {
  oninit: function () {
    this.isLoading = false;
  },

  view: function (vnode) {
    const labelMessage = vnode.attrs.isLocked
      ? `Unlock ${vnode.attrs.contentTitle}`
      : `Lock ${vnode.attrs.contentTitle}`;

    const iconClassName = () => {
      if (this.isLoading) return "fa-spinner fa-spin lock-loading";

      if (vnode.attrs.isLocked) {
        return "fa-lock";
      } else {
        return "fa-lock-open";
      }
    };

    return m(
      "button",
      {
        class: "action-btn",
        ariaLabel: labelMessage,
        title: labelMessage,
        disabled: this.isLoading,
        onclick: async () => {
          if (this.isLoading) {
            return;
          }

          this.isLoading = true;
          m.redraw();

          try {
            await Contents.lock(vnode.attrs.contentId);
          } catch (err) {
            console.error(err);
            const action = vnode.attrs.isLocked ? "unlock" : "lock";
            notifyError(
              `Couldn't ${action} "${vnode.attrs.contentTitle}": ${reason(err)}`,
            );
          } finally {
            this.isLoading = false;
            m.redraw();
          }
        },
      },
      [
        m("i", {
          class: `fa-solid ${iconClassName()}`,
        }),
      ],
    );
  },
};

export default LockContentButton;
