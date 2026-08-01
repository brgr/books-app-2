import { beforeEach, describe, expect, it } from "vitest";
import { invalidateCache } from "./invalidate";
import { cacheKeys } from "./keys";
import { cacheClear, cacheGet, cacheSet } from "./store";
import { ShelfName } from "../api/types";

const shelfPage = cacheKeys.shelfBooks(ShelfName.STARTED, 1, 20);
const otherShelfPage = cacheKeys.shelfBooks(ShelfName.FINISHED, 1, 20);

/** Everything a mutation could plausibly touch, so each case can assert what survives as well as what goes. */
async function seed() {
  await cacheSet(shelfPage, "shelf page");
  await cacheSet(otherShelfPage, "other shelf page");
  await cacheSet(cacheKeys.book(42), "book 42");
  await cacheSet(cacheKeys.bookEvents(42), "book 42 events");
  await cacheSet(cacheKeys.book(7), "book 7");
  await cacheSet(cacheKeys.bookEvents(7), "book 7 events");
}

async function survivors() {
  const keys = [
    shelfPage,
    otherShelfPage,
    cacheKeys.book(42),
    cacheKeys.bookEvents(42),
    cacheKeys.book(7),
    cacheKeys.bookEvents(7),
  ];
  const present = await Promise.all(keys.map(async (key) => ((await cacheGet(key)) ? key : null)));
  return present.filter((key) => key !== null);
}

describe("invalidateCache", () => {
  beforeEach(async () => {
    await cacheClear();
    await seed();
  });

  it("drops every shelf page when a book is added", async () => {
    await invalidateCache.bookAdded();

    expect(await survivors()).toEqual([
      cacheKeys.book(42),
      cacheKeys.bookEvents(42),
      cacheKeys.book(7),
      cacheKeys.bookEvents(7),
    ]);
  });

  it("drops the book and the shelves when a book is updated", async () => {
    await invalidateCache.bookUpdated(42);

    // The timeline is untouched: editing metadata records no event
    expect(await survivors()).toEqual([cacheKeys.bookEvents(42), cacheKeys.book(7), cacheKeys.bookEvents(7)]);
  });

  it("drops the book, its timeline and the shelves when a book is deleted", async () => {
    await invalidateCache.bookDeleted(42);

    expect(await survivors()).toEqual([cacheKeys.book(7), cacheKeys.bookEvents(7)]);
  });

  // This is a regression test as we erroneously did this in the past
  it("keeps books whose id merely starts with the deleted one", async () => {
    await cacheSet(cacheKeys.book(4), "book 4");
    await cacheSet(cacheKeys.bookEvents(4), "book 4 events");

    await invalidateCache.bookDeleted(4);

    // "books:4" is a string prefix of "books:42", so a prefix sweep would take book 42 down with it
    expect(await cacheGet(cacheKeys.book(4))).toBeUndefined();
    expect(await cacheGet(cacheKeys.bookEvents(4))).toBeUndefined();
    expect(await cacheGet(cacheKeys.book(42))).toBeDefined();
    expect(await cacheGet(cacheKeys.bookEvents(42))).toBeDefined();
  });

  it("drops the book, its timeline and the shelves when the shelf changes", async () => {
    await invalidateCache.shelfChanged(42);

    expect(await survivors()).toEqual([cacheKeys.book(7), cacheKeys.bookEvents(7)]);
  });

  it("drops only the timeline when notes are saved", async () => {
    await invalidateCache.notesSaved(42);

    // The book itself is written through by the caller, and notes show nowhere on a shelf
    expect(await survivors()).toEqual([
      shelfPage,
      otherShelfPage,
      cacheKeys.book(42),
      cacheKeys.book(7),
      cacheKeys.bookEvents(7),
    ]);
  });

  it("drops the timeline and the shelves when progress is saved", async () => {
    await invalidateCache.progressSaved(42);

    // Shelf tiles render the progress, so their pages go too
    expect(await survivors()).toEqual([cacheKeys.book(42), cacheKeys.book(7), cacheKeys.bookEvents(7)]);
  });
});
