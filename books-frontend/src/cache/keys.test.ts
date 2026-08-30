import { describe, it, expect } from "vitest";
import { cacheKeys } from "./keys";

describe("cacheKeys", () => {
  it("generates key for shelf books with pagination", () => {
    expect(cacheKeys.shelfBooks("reading:started", 1, 20)).toBe("shelves:reading:started:books:page=1&pageSize=20");
  });

  it("generates key for a single book", () => {
    expect(cacheKeys.book(42)).toBe("books:42");
  });

  it("generates key for book events", () => {
    expect(cacheKeys.bookEvents(42)).toBe("books:42:events");
  });

  it("generates invalidation prefixes that cover the matching keys", () => {
    expect(cacheKeys.shelfBooks("reading:started", 1, 20).startsWith(cacheKeys.shelvesPrefix())).toBe(true);
    expect(
      cacheKeys.shelfBooks("reading:started", 1, 20).startsWith(cacheKeys.shelfBooksPrefix("reading:started")),
    ).toBe(true);
  });
});
