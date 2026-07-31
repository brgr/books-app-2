import { describe, it, expect } from "vitest";
import { cacheKeys } from "./keys";
import { ShelfName } from "../api/types";

describe("cacheKeys", () => {
  it("generates key for shelf books with pagination", () => {
    expect(cacheKeys.shelfBooks(ShelfName.STARTED, 1, 20)).toBe("shelves:started:books:page=1&pageSize=20");
  });

  it("generates key for a single book", () => {
    expect(cacheKeys.book(42)).toBe("books:42");
  });

  it("generates key for book events", () => {
    expect(cacheKeys.bookEvents(42)).toBe("books:42:events");
  });

  it("generates invalidation prefixes that cover the matching keys", () => {
    expect(cacheKeys.shelfBooks(ShelfName.STARTED, 1, 20).startsWith(cacheKeys.shelvesPrefix())).toBe(true);
    expect(cacheKeys.book(42).startsWith(cacheKeys.bookPrefix(42))).toBe(true);
    expect(cacheKeys.bookEvents(42).startsWith(cacheKeys.bookPrefix(42))).toBe(true);
  });
});
