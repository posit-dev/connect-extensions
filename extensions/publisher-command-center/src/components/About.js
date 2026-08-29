import m from "mithril";

import { formatDate, formatRelative } from "../utils/dates";
import Content from "../models/Content";

const About = {
  view: function () {
    // Reads the content that Edit has already loaded into the Content model.
    const content = Content.data;
    if (content === null) {
      return "";
    }

    const desc = content?.description;
    const updated = content?.last_deployed_time;
    const created = content?.created_time;

    return m(".pt-3.border-top", [
      m(".", [
        m("h5", "About"),
        m("p", desc || m("i", "No Description")),
        m(
          "p",
          m("small.text-body-secondary", "Updated " + formatRelative(updated)),
        ),
        m(
          "p",
          m(
            "small.text-body-secondary",
            "Created on " + formatDate(created, "MMMM do, yyyy"),
          ),
        ),
      ]),
    ]);
  },
};

export default About;
