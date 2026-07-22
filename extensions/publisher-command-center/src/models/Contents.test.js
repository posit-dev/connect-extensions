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

describe("Contents.delete", () => {
  it("sends DELETE to the content's route and drops it from data", async () => {
    Contents.data = [{ guid: "g1" }, { guid: "g2" }];
    m.request.mockResolvedValue(undefined);

    await Contents.delete("g1");

    expect(m.request).toHaveBeenCalledWith({
      method: "DELETE",
      url: "api/contents/g1",
    });
    expect(Contents.data).toEqual([{ guid: "g2" }]);
  });
});

describe("Contents.lock", () => {
  it("sends PATCH to the lock route and merges the response into the item", async () => {
    Contents.data = [{ guid: "g1", locked: false }];
    m.request.mockResolvedValue({ guid: "g1", locked: true });

    await Contents.lock("g1");

    expect(m.request).toHaveBeenCalledWith({
      method: "PATCH",
      url: "api/contents/g1/lock",
    });
    expect(Contents.data[0].locked).toBe(true);
  });
});

describe("Contents.rename", () => {
  it("sends PATCH to the rename route with the new title and merges the response", async () => {
    Contents.data = [{ guid: "g1", title: "Old" }];
    m.request.mockResolvedValue({ guid: "g1", title: "New" });

    await Contents.rename("g1", "New");

    expect(m.request).toHaveBeenCalledWith({
      method: "PATCH",
      url: "api/contents/g1/rename",
      body: { title: "New" },
    });
    expect(Contents.data[0].title).toBe("New");
  });
});
