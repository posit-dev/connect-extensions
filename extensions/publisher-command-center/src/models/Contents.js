import m from "mithril";

export default {
  data: null,
  _fetch: null,

  load: function () {
    if (this.data) {
      return Promise.resolve(this.data);
    }

    if (this._fetch) {
      return this._fetch;
    }

    this._fetch = m
      .request({ method: "GET", url: `api/contents` })
      .then((result) => {
        this.data = result;
        this._fetch = null;
      })
      .catch((err) => {
        this._fetch = null;
        throw err;
      });
  },

  delete: async function (guid) {
    await m.request({
      method: "DELETE",
      url: `api/contents/${guid}`,
    });

    this.data = this.data.filter((c) => c.guid !== guid);
  },

  lock: async function (guid) {
    await m.request({
      method: "PATCH",
      url: `api/content/${guid}/lock`,
    }).then((response) => {
      const targetContent = this.data.find((c) => c.guid === guid);
      Object.assign(targetContent, response);
    });
  },

  rename: async function (guid, newName) {
    await m.request({
      method: "PATCH",
      url: `api/content/${guid}/rename`,
      body: {
        title: newName,
      },
    });
  },

  reset: function () {
    this.data = null;
    this._fetch = null;
  },
};
