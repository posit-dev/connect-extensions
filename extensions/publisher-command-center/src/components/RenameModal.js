import m from "mithril";
import Contents from "../models/Contents";

const RenameModalForm = {
  newName: "",
  guid: "",
  isValid: false,
  onsubmit: function(e) {
    if (RenameModalForm.isValid) {
      e.preventDefault();  
      Contents.rename(RenameModalForm.guid, RenameModalForm.newName);

      const modalEl = document.getElementById(`renameModal-${RenameModalForm.guid}`);
      const modal = bootstrap.Modal.getInstance(modalEl);
      modal.hide();
    }
  },
  view: function(vnode) {
    return m("form", {
        onsubmit: (e) => { this.onsubmit(e); }
      },
      [
        m("section", { class: "modal-body" }, [
          m("div", { class: "form-group has-validation" }, [
            m("label", {
              for: "rename-content-input",
              class: "mb-3",
            }, "Enter new name for ", [
              m("span", { class: "fw-bold" }, `${vnode.attrs.contentTitle}`)
            ]),
            m("input", {
              oninput: function(e) {
                RenameModalForm.isValid = e.target.validity.valid;
                RenameModalForm.guid = vnode.attrs.contentId;
                RenameModalForm.newName = e.target.value;
              },
              id: "rename-content-input",
              type: "text",
              class: "form-control",
              required: true,
              minlength: 3,
              maxlength: 1024,
            }),
          ])
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
    ])
  },
}

const RenameModal = {
  view: function(vnode) {
    return m("div", {
        class: "modal",
        id: `renameModal-${vnode.attrs.contentId}`,
        tabindex: "-1",
        ariaHidden: true
      }, [
      m("div", { class: "modal-dialog modal-dialog-centered" }, [
        m("div", { class: "modal-content" }, [
          m("div", { class: "modal-header"}, [
            m("h1", { class: "modal-title fs-6" }, "Rename Content"),
            m("button", {
              class: "btn-close",
              ariaLabel: "Close modal",
              "data-bs-dismiss": "modal"
            }),
          ]),
          m(RenameModalForm, {
            contentTitle: vnode.attrs.contentTitle,
            contentId: vnode.attrs.contentId,
          })
        ]),
      ]),
    ])
  },
};

export default RenameModal;
