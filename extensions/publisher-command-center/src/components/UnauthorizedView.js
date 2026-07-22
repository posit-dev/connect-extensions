import m from "mithril";

// Shown when the app isn't authorized: a concise setup card for adding the
// Connect Visitor API Key integration by hand, so the app never lists or
// manages content with the deployer's credentials. The admin prerequisite and
// Max Role requirement live in the README.
const UnauthorizedView = {
  view: function () {
    const oauthDocsUrl =
      "https://docs.posit.co/connect/user/oauth-integrations/";

    return m(
      "div.d-flex.align-items-center.justify-content-center.bg-body-secondary.p-4",
      { style: { minHeight: "100vh" } },
      m(
        "div.card.shadow-sm",
        { style: { maxWidth: "28rem", width: "100%" } },
        m("div.card-body.p-4", [
          m("h1.h5.text-center.mb-3", "Setup"),
          m("p.text-body-secondary", [
            'This app needs a "Connect Visitor API Key" integration to list and manage content as you, the signed-in viewer. In the content settings, on the ',
            m("strong", "Access"),
            ' tab, add the "Connect Visitor API Key" integration under ',
            m("strong", "Integrations"),
            ".",
          ]),
          m("p.text-body-secondary.mb-0", [
            "For more information, see the ",
            m(
              "a",
              { href: oauthDocsUrl, target: "_blank", rel: "noopener" },
              "OAuth Integrations documentation",
            ),
            ".",
          ]),
        ]),
      ),
    );
  },
};

export default UnauthorizedView;
