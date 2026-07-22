import { describe, it, expect, vi, beforeEach } from "vitest";

import m from "mithril";
import Processes from "./Processes";

vi.mock("mithril", () => ({ default: { request: vi.fn() } }));

beforeEach(() => {
  m.request.mockReset();
});

describe("Processes.destroy", () => {
  it("sends DELETE to the process's route under the content", () => {
    Processes.destroy("c1", "p1");

    expect(m.request).toHaveBeenCalledWith({
      method: "DELETE",
      url: "api/contents/c1/processes/p1",
    });
  });
});
