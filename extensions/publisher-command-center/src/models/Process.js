import m from "mithril";

const Process = {
  destroy: function (content_id, process_id) {
    return m.request({
      method: "DELETE",
      url: `api/contents/${content_id}/processes/${process_id}`,
    });
  },
};

export default Process;
