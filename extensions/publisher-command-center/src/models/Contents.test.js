import { describe, it, expect, vi, beforeEach } from "vitest";

import m from "mithril";
import Contents from "./Contents";

vi.mock("mithril", () => ({ default: { request: vi.fn() } }));

beforeEach(() => {
  Contents.reset();
  m.request.mockReset();
});

describe("Contents.load", () => {
  it("returns a promise that resolves with the fetched data", async () => {
    m.request.mockResolvedValue([{ guid: "g1" }]);

    const result = Contents.load();
    // load() must return its promise so callers can attach .then/.catch.
    expect(typeof result.then).toBe("function");

    await result;
    expect(Contents.data).toEqual([{ guid: "g1" }]);
  });

  it("propagates a rejection to the caller", async () => {
    m.request.mockRejectedValue(new Error("boom"));
    await expect(Contents.load()).rejects.toThrow("boom");
  });

  it("caches: a second load() does not re-request", async () => {
    m.request.mockResolvedValue([{ guid: "g1" }]);
    await Contents.load();
    await Contents.load();
    expect(m.request).toHaveBeenCalledTimes(1);
  });
});
