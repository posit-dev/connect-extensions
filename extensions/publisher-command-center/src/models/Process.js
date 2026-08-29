import m from "mithril";

const Process = {
  destroy: function (contentId, processId) {
    return m.request({
      method: "DELETE",
      url: `api/contents/${contentId}/processes/${processId}`,
    });
  },
};

export default Process;
