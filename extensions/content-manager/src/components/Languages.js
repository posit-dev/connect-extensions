import m from "mithril";

// api - R code defining a Plumber API.

// jupyter-voila A Voila interactive dashboard.

const getLanguages = (content) => {
  const languages = new Set();

  switch (content?.app_mode) {
    case "jupyter-static":
    case "jupyter-static":
    case "python-api":
    case "python-bokeh":
    case "python-dash":
    case "python-fastapi":
    case "python-gradio":
    case "python-shiny":
    case "python-streamlit":
    case "tensorflow-saved-model":
      languages.add("Python");
      break;
    case "quarto-shiny":
    case "quarto-static":
      languages.add("Quarto");
      break;
    case "rmd-shiny":
    case "rmd-static":
    case "shiny":
      languages.add("R");
      break;
    case "static":
      languages.add("Static");
      break;
    default:
      break;
  }

  switch (content?.content_category) {
    case "plot":
      languages.add("Static")
      languages.add("Plot");
      break;
    case "pin":
      languages.add("Static");
      languages.add("Pin")
      break;
    case "rmd-static":
      languages.add("Static")
      languages.add("Site")
      break;
    default:
      break;
  }

  if (content["r_version"] != null && content["r_version"] !== "") {
    languages.add("R");
  }
  if (content["py_version"] != null && content["py_version"] !== "") {
    languages.add("Python");
  }
  if (content["quarto_version"] != null && content["quarto_version"] !== "") {
    languages.add("Quarto");
  }
  if (content["content_category"] === "pin") {
    languages.add("Pin");
  }

  return [...languages].sort();
};

export default {
  view: function (vnode) {
    const languages = getLanguages(vnode.attrs);
    return languages.map((language) => {
      return m("span", { class: "mx-1 badge text-bg-primary" }, language);
    });
  },
};
