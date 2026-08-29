import { describe, it, expect, afterEach } from "vitest";

import About from "./About";
import Content from "../models/Content";

afterEach(() => {
  Content.reset();
});

describe("About", () => {
  // Regression guard: About must stay presentational. It previously re-loaded
  // the Content model with an id it was never passed, and reset the model on
  // removal, which clobbered the content Edit had already loaded.
  it("has no lifecycle hooks that load or reset content", () => {
    expect(About.oninit).toBeUndefined();
    expect(About.onremove).toBeUndefined();
  });

  it("renders nothing until Edit has loaded the content", () => {
    Content.data = null;
    expect(About.view()).toBe("");
  });

  it("renders from the content Edit loaded into the model", () => {
    Content.data = {
      description: "My app",
      last_deployed_time: "2026-01-01T00:00:00Z",
      created_time: "2026-01-01T00:00:00Z",
    };

    const vnode = About.view();

    expect(vnode).toBeTruthy();
    expect(vnode.tag).toBe("div"); // m(".pt-3.border-top") renders a <div>
  });
});
