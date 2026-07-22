import m from "mithril";
import Contents from "../models/Contents";
import { Modal } from "bootstrap";
import { notifyError, reason } from "../utils/notify";

const RenameModalForm = {
  onsubmit: function (e, contentId) {
    e.preventDefault();
    // Read the title from this form's own input rather than shared module state,
    // so a reused modal can never submit a stale guid or an empty title.
    const input = e.target.querySelector("input");
    if (!input || !input.validity.valid) {
      return;
    }
    // Only close the modal and clear the field once the rename succeeds; on
    // failure keep it open and surface the error.
    Contents.rename(contentId, input.value)
      .then(() => {
        const modalEl = document.getElementById(`renameModal-${contentId}`);
        Modal.getInstance(modalEl)?.hide();
        input.value = "";
      })
      .catch((err) => {
        console.error(err);
        notifyError(`Couldn't rename the content: ${reason(err)}`);
      });
  },
  view: function (vnode) {
    return m(
      "form",
      {
        onsubmit: (e) => RenameModalForm.onsubmit(e, vnode.attrs.contentId),
      },
      [
        m("section", { class: "modal-body" }, [
          m("div", { class: "form-group" }, [
            m(
              "label",
              {
                for: `rename-content-input-${vnode.attrs.contentId}`,
                class: "mb-3",
              },
              "Enter new name for ",
              [m("span", { class: "fw-bold" }, `${vnode.attrs.contentTitle}`)],
            ),
            m("input", {
              id: `rename-content-input-${vnode.attrs.contentId}`,
              type: "text",
              class: "form-control",
              required: true,
              minlength: 3,
              maxlength: 1024,
            }),
          ]),
        ]),
        m("div", { class: "modal-footer" }, [
          m(
            "button",
            {
              type: "submit",
              class: "btn btn-primary",
              ariaLabel: "Rename Content",
            },
            "Rename Content",
          ),
        ]),
      ],
    );
  },
};

const RenameModal = {
  view: function (vnode) {
    return m(
      "div",
      {
        class: "modal",
        id: `renameModal-${vnode.attrs.contentId}`,
        tabindex: "-1",
        ariaHidden: true,
      },
      [
        m("div", { class: "modal-dialog modal-dialog-centered" }, [
          m("div", { class: "modal-content" }, [
            m("div", { class: "modal-header" }, [
              m("h1", { class: "modal-title fs-6" }, "Rename Content"),
              m("button", {
                class: "btn-close",
                ariaLabel: "Close modal",
                "data-bs-dismiss": "modal",
              }),
            ]),
            m(RenameModalForm, {
              contentTitle: vnode.attrs.contentTitle,
              contentId: vnode.attrs.contentId,
            }),
          ]),
        ]),
      ],
    );
  },
};

export default RenameModal;
