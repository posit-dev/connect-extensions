import m from "mithril";

import { format } from 'date-fns';

const Content = {
    data: null,
    error: null,

    oninit: async (vnode) => {
        const guid = vnode.attrs.guid
        try {
            Content.data = await m.request({ method: "GET", url: `contents/${guid}` })
        } catch (err) {
            Content.error = "Failed to load content."
            console.error(err)
        }
    },

    view: () => {
        return ""
    }
}

const Contents = {
    // Component state
    data: [],
    error: null,

    // Lifecycle method for data fetching
    oninit: async () => {
        try {
            Contents.data = await m.request({ method: "GET", url: "contents" })
        } catch (err) {
            Contents.error = "Failed to load data.";
            console.error(err);
        }
    },

    // View method for rendering
    view: () => {
        if (Contents.error) {
            return m("div", { class: "error" }, Contents.error);
        }

        if (Contents.data.length === 0) {
            return m("div", "Loading...");
        }

        return m("table", { class: "table" },
            m("thead",
                m("tr", [
                    m("th", { scope: "col" }, ""),
                    m("th", { scope: "col" }, "Title"),
                    m("th", { scope: "col" }, "Language"),
                    m("th", { scope: "col" }, "Last Updated"),
                    m("th", { scope: "col" }, "Date Added"),
                ])
            ),
            m("tbody", Contents.data.map(content => {
                const languages = Contents._parse_languages(content)
                return m("tr", { style: "cursor: pointer" }, [
                    m("td",
                        m("a", { class: "fa-solid fa-arrow-up-right-from-square", href: content["content_url"], target: "_blank" })
                    ),
                    m("td", content["title"]),
                    m("td", languages.map(language => {
                        return m("span", { class: "mx-1 badge text-bg-primary" }, language)
                    })),
                    m("td", format(content["last_deployed_time"], "MMM do, yyyy")),
                    m("td", format(content["created_time"], "MMM do, yyyy")),
                ])
            }))
        )
    },

    _parse_languages: (content) => {
        var languages = []
        if (content["r_version"] != null && content["r_version"] !== "") {
            languages.push("R");
        }

        if (content["py_version"] != null && content["py_version"] !== "") {
            languages.push("Python");
        }

        if (content["quarto_version"] != null && content["quarto_version"] !== "") {
            languages.push("Quarto");
        }

        if (content["content_category"] === "pin") {
            languages.push("Pin")
        }
        return languages
    }
};


export const App = () => {
    return {
        view: () => {
            return m("div", { class: "container" },
                m("h1", { class: "display-1" }, "Content Manager"),
                m("p", { class: "lead" }, "Manage your content and their settings here."),
                m(Contents)
            )
        }
    };
};
