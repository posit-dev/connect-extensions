import m from "mithril";
import Contents from "../models/Contents";

const LockedContentButton = {  
  view: function(vnode) {
    const labelMessage = vnode.attrs.isLocked ? "Unlock Content" : "Lock Content";
    const iconClassName = vnode.attrs.isLocked ? "fa-lock" : "fa-lock-open";
    return m("button", {
      class: "action-btn",
      ariaLabel: labelMessage,
      title: labelMessage,
      onclick: () => {
        Contents.lock(vnode.attrs.contentId)
      }
    }, [
      m("i", { class: `fa-solid ${iconClassName}` })
    ])
  }
};

export default LockedContentButton;
