import m from "mithril";
import Contents from "../models/Contents";

const LockedContentButton = {
  oninit: function () {
    this.isLoading = false;
  },

  view: function(vnode) {
    const labelMessage = vnode.attrs.isLocked ?
       `Unlock ${vnode.attrs.contentTitle}` :
       `Lock Content ${vnode.attrs.contentTitle}`;

    const iconClassName = () => {
      if (this.isLoading) return "fa-spinner fa-spin lock-loading";

      if (vnode.attrs.isLocked) {
        return "fa-lock";
      } else {
        return "fa-lock-open";
      }
    };

    return m("button", {
      class: "action-btn",
      ariaLabel: labelMessage,
      title: labelMessage,
      disabled: this.isLoading,
      onclick: async () => {
        if (this.isLoading) { return; }

        this.isLoading = true;
        m.redraw();

        try {
          await Contents.lock(vnode.attrs.contentId)
        } finally {
          this.isLoading = false;
          m.redraw();
        }
      }
    }, [
      m("i", {
        class: `fa-solid ${iconClassName()}`,

        }
      )
    ])
  }
};

export default LockedContentButton;
