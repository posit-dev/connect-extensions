import m from "mithril";

const UnauthorizedView = {
  oninit: function (vnode) {
    vnode.state.integration = null;
    vnode.state.loading = true;

    // Check for available integration
    m.request({ method: "GET", url: "api/integrations" })
      .then(response => {
        vnode.state.integration = response;
        vnode.state.loading = false;
        m.redraw();
      })
      .catch(err => {
        console.error("Failed to fetch integrations", err);
        vnode.state.loading = false;
        m.redraw();
      });
  },

  addIntegration: function (vnode) {
    if (!vnode.state.integration) return;

    m.request({
      method: "PUT",
      url: "api/visitor-auth",
      body: { integration_guid: vnode.state.integration.guid }
    })
      .then(() => {
        // Reload the top-most window to check authorization again
        window.top.location.reload();
      })
      .catch(err => {
        console.error("Failed to add integration", err);
      });
  },

  view: function (vnode) {
    // Show loading state
    if (vnode.state.loading) {
      return m("div.d-flex.justify-content-center", { style: { margin: "3rem" } }, [
        m("div.spinner-border.text-primary", { role: "status" },
          m("span.visually-hidden", "Loading...")
        )
      ]);
    }

    // We have an integration ready to add
    if (vnode.state.integration) {
      return m("div.alert.alert-info", {
        style: {
          margin: "1rem auto",
          maxWidth: "640px",
          width: "calc(100% - 2rem)"
        }
      }, [
        m("div", { style: { marginBottom: "1rem" } }, [
          m("p", [
            "This content uses a ",
            m("strong", "Visitor API Key"),
            " integration to show users the content they have access to.",
            " A compatible integration is already available; use it below."
          ]),
          m("p", [
            "For more information, see ",
            m("a", {
              href: "https://docs.posit.co/connect/user/oauth-integrations/#obtaining-a-visitor-api-key",
              target: "_blank"
            }, "documentation on Visitor API Key integrations")
          ])
        ]),
        m("button.btn.btn-primary", {
          onclick: () => this.addIntegration(vnode)
        }, [
          m("i.fas.fa-plus.me-2"),
          "Use the ",
          m("strong", vnode.state.integration.title || vnode.state.integration.name || "Connect API"),
          " Integration"
        ])
      ]);
    }

    // No integration available
    const baseUrl = window.location.origin;
    const integrationSettingsUrl = `${baseUrl}/connect/#/system/integrations`;

    return m("div.alert.alert-warning", {
      style: {
        margin: "1rem auto",
        maxWidth: "640px",
        width: "calc(100% - 2rem)"
      }
    }, [
      m("div", { style: { marginBottom: "1rem" } }, [
        m("p", "This content needs permission to show users the content they have access to."),
        m("p", [
          "To allow this, an Administrator must configure a ",
          m("strong", "Connect API"),
          " integration on the ",
          m("strong", [
            m("a", { href: integrationSettingsUrl, target: "_blank" }, "Integration Settings")
          ]),
          " page."
        ]),
        m("p", [
          "On that page, select ",
          m("strong", "+ Add Integration"),
          ". In the 'Select Integration' dropdown, choose ",
          m("strong", "Connect API"),
          ". The 'Max Role' field must be set to ",
          m("strong", "Administrator"),
          " or ",
          m("strong", "Publisher"),
          "; 'Viewer' will not work."
        ]),
        m("p", [
          "See the ",
          m("a", {
            href: "https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/",
            target: "_blank"
          }, "Connect API section of the Admin Guide"),
          " for more detailed setup instructions."
        ])
      ])
    ]);
  }
};

export default UnauthorizedView;
