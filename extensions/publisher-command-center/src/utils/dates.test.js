import { describe, it, expect } from "vitest";

import { formatDate, formatRelative } from "./dates";

describe("formatDate", () => {
  it("formats a valid date", () => {
    // Date-only input parses to local midnight, so the formatted date is
    // timezone-independent.
    expect(formatDate("2025-03-19", "yyyy-MM-dd")).toBe("2025-03-19");
  });

  it("returns the fallback for null/undefined (the null-date guard)", () => {
    expect(formatDate(null, "yyyy-MM-dd")).toBe("Unknown");
    expect(formatDate(undefined, "yyyy-MM-dd", "n/a")).toBe("n/a");
  });

  it("returns the fallback for an unparseable value instead of throwing", () => {
    expect(formatDate("not-a-date", "yyyy-MM-dd")).toBe("Unknown");
  });
});

describe("formatRelative", () => {
  it("formats a valid timestamp with a suffix", () => {
    const threeHoursAgo = new Date(
      Date.now() - 3 * 60 * 60 * 1000,
    ).toISOString();
    expect(formatRelative(threeHoursAgo)).toMatch(/ago$/);
  });

  it("returns the fallback for null/invalid instead of throwing", () => {
    expect(formatRelative(null)).toBe("unknown");
    expect(formatRelative("nope")).toBe("unknown");
  });
});
