import m from "mithril";

const UnauthorizedView = {
  oninit: function(vnode) {
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

  addIntegration: function(vnode) {
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

  view: function(vnode) {
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
      return m("div.alert.alert-info", { style: { margin: "1rem auto", maxWidth: "800px" } }, [
        m("div", { style: { marginBottom: "1rem" } }, [
          m.trust("This content uses a <strong>Visitor API Key</strong> " +
            "integration to show users the content they have access to. " +
            "A compatible integration is displayed below." +
            "<br><br>" +
            "For more information, see " +
            "<a href='https://docs.posit.co/connect/user/oauth-integrations/#obtaining-a-visitor-api-key' " +
            "target='_blank'>documentation on Visitor API Key integrations</a>.")
        ]),
        m("button.btn.btn-primary", {
          onclick: () => this.addIntegration(vnode)
        }, [
          m("i.fas.fa-plus.me-2"),
          m.trust("Add the <strong>'" + (vnode.state.integration.title || vnode.state.integration.name || "Connect API") + "'</strong> Integration")
        ])
      ]);
    }

    // No integration available
    const baseUrl = window.location.origin;
    const integrationSettingsUrl = `${baseUrl}/connect/#/system/integrations`;

    return m("div.alert.alert-warning", { style: { margin: "1rem auto", maxWidth: "800px" } }, [
      m("div", { style: { marginBottom: "1rem" } }, [
        m.trust("This content needs permission to show users the content they have access to." +
          "<br><br>" +
          "To allow this, an Administrator must configure a " +
          "<strong>Connect API</strong> integration on the " +
          "<strong><a href='" + integrationSettingsUrl + "' target='_blank'>Integration Settings</a></strong> page. " +
          "<br><br>" +
          "On that page, select <strong>'+ Add Integration'</strong>. " +
          "In the 'Select Integration' dropdown, choose <strong>'Connect API'</strong>. " +
          "The 'Max Role' field must be set to <strong>'Administrator'</strong> " +
          "or <strong>'Publisher'</strong>; 'Viewer' will not work. " +
          "<br><br>" +
          "See the <a href='https://docs.posit.co/connect/admin/integrations/oauth-integrations/connect/' " +
          "target='_blank'>Connect API section of the Admin Guide</a> for more detailed setup instructions.")
      ])
    ]);
  }
};

export default UnauthorizedView;
