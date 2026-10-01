import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";

vi.mock("mithril", () => ({ default: { redraw: vi.fn() } }));

import { notifications, notifyError, dismiss, reason } from "./notify";

beforeEach(() => {
  notifications.length = 0;
  vi.useFakeTimers();
});

afterEach(() => {
  vi.useRealTimers();
});

describe("notify", () => {
  it("notifyError queues a message", () => {
    notifyError("boom");
    expect(notifications).toHaveLength(1);
    expect(notifications[0].message).toBe("boom");
  });

  it("dismiss removes the matching notification", () => {
    const id = notifyError("x");
    dismiss(id);
    expect(notifications).toHaveLength(0);
  });

  it("auto-dismisses after the timeout", () => {
    notifyError("temporary");
    expect(notifications).toHaveLength(1);
    vi.advanceTimersByTime(8000);
    expect(notifications).toHaveLength(0);
  });
});

describe("reason", () => {
  it("returns the server-provided detail when present", () => {
    expect(reason({ response: { detail: "content is locked" } })).toBe(
      "content is locked",
    );
  });

  it("falls back when there is no detail", () => {
    expect(reason(new Error("x"))).toBe("Please try again.");
    expect(reason(undefined)).toBe("Please try again.");
    expect(reason({ response: {} }, "custom")).toBe("custom");
  });
});
