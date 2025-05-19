import m from "mithril";

const Content = {
  data: null,
  _fetch: null,

  load: function (id) {
    if (this.data) {
      return Promise.resolve(this.data);
    }

    if (this._fetch) {
      return this._fetch;
    }

    this._fetch = m
      .request({ method: "GET", url: `api/contents/${id}` })
      .then((result) => {
        this.data = result;
        this._fetch = null;
      })
      .catch((err) => {
        this._fetch = null;
        throw err;
      });
  },

  delete: function (content_id) {
    return m.request({
      method: "DELETE",
      url: `api/content/${content_id}/`,
    });
  },

  reset: function () {
    this.data = null;
    this._fetch = null;
  },
};

export default Content;
