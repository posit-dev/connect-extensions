import m from "mithril";

// Surfaces the otherwise-invisible identity mechanism: the app calls Connect as
// the signed-in viewer through a Visitor API Key, so each person sees and manages
// only the content they already have access to (no shared admin key).
export default {
  user: null,

  oninit: function () {
    m.request({ method: "GET", url: "api/user" })
      .then((user) => {
        this.user = user;
        m.redraw();
      })
      .catch(() => {
        // Non-fatal: the panel just falls back to "you" without a name.
      });
  },

  view: function () {
    const user = this.user;
    const name =
      (user &&
        (`${user.first_name || ""} ${user.last_name || ""}`.trim() ||
          user.username)) ||
      "you";

    return m(
      ".alert.alert-light.border.d-flex.align-items-start.gap-2",
      { role: "note" },
      [
        m("i.fa-solid.fa-circle-info.mt-1.text-secondary"),
        m("small.text-secondary", [
          "Acting as ",
          m("strong", name),
          ". This app calls Connect as you through a Visitor API Key, so you see " +
            "and manage only the content you already have access to; no shared " +
            "admin key is stored.",
        ]),
      ],
    );
  },
};
