import m from "mithril";
import Contents from "../models/Contents";
import { notifyError, reason } from "../utils/notify";

const ConfirmDeleteButton = {
  view(vnode) {
    return m(
      "button",
      {
        class: "btn btn-primary",
        ariaLabel: "Yes",
        "data-bs-dismiss": "modal",
        onclick: () => {
          Contents.delete(vnode.attrs.contentId).catch((err) => {
            console.error(err);
            notifyError(
              `Couldn't delete "${vnode.attrs.contentTitle}": ${reason(err)}`,
            );
          });
        },
      },
      "Yes",
    );
  },
};

const CancelDeleteButton = {
  view(_vnode) {
    return m(
      "button",
      {
        class: "btn btn-secondary",
        ariaLabel: "No",
        "data-bs-dismiss": "modal",
      },
      "No",
    );
  },
};

const DeleteModal = {
  view: function (vnode) {
    return m(
      "div",
      {
        class: "modal",
        id: `deleteModal-${vnode.attrs.contentId}`,
        tabindex: "-1",
        ariaHidden: true,
      },
      [
        m("div", { class: "modal-dialog modal-dialog-centered" }, [
          m("div", { class: "modal-content" }, [
            m("div", { class: "modal-header" }, [
              m("h1", { class: "modal-title fs-6" }, "Delete Content"),
              m("button", {
                class: "btn-close",
                ariaLabel: "Close modal",
                "data-bs-dismiss": "modal",
              }),
            ]),
            m("section", { class: "modal-body" }, [
              m(
                "p",
                { class: "mb-3" },
                `Are you sure you want to delete ${vnode.attrs.contentTitle}?`,
              ),
            ]),
            m("div", { class: "modal-footer" }, [
              m(CancelDeleteButton),
              m(ConfirmDeleteButton, {
                contentId: vnode.attrs.contentId,
                contentTitle: vnode.attrs.contentTitle,
              }),
            ]),
          ]),
        ]),
      ],
    );
  },
};

export default DeleteModal;
