import { cacheKeys } from "./keys";
import { cacheDel, cacheInvalidateByPrefix } from "./store";

interface Targets {
  /** Exact keys to drop. */
  keys?: string[];
  /** Key prefixes to drop, covering every entry below them (e.g. all cached pages of a shelf). */
  prefixes?: string[];
}

async function drop(targets: Targets): Promise<void> {
  await Promise.all([...(targets.keys ?? []).map(cacheDel), ...(targets.prefixes ?? []).map(cacheInvalidateByPrefix)]);
}

/**
 * What each change makes stale.
 *
 * Callers name the change they just performed and this decides which entries go.
 */
export const invalidateCache = {
  bookAdded: () => drop({ prefixes: [cacheKeys.shelvesPrefix()] }),

  bookUpdated: (bookId: number) => drop({ keys: [cacheKeys.book(bookId)], prefixes: [cacheKeys.shelvesPrefix()] }),

  bookDeleted: (bookId: number) =>
    drop({
      keys: [cacheKeys.book(bookId), cacheKeys.bookEvents(bookId)],
      prefixes: [cacheKeys.shelvesPrefix()],
    }),

  shelfChanged: (bookId: number) =>
    drop({
      keys: [cacheKeys.book(bookId), cacheKeys.bookEvents(bookId)],
      prefixes: [cacheKeys.shelvesPrefix()],
    }),

  // The book itself is written directly into the cache, but the timeline is not; it's not really possible
  // to know what the timeline will look like after a note is added (only the server knows its datetime, for example),
  // so we just drop it and let it be refetched.
  notesSaved: (bookId: number) => drop({ keys: [cacheKeys.bookEvents(bookId)] }),

  // Shelf tiles render the reading progress, so their cached pages go stale along with the timeline.
  progressSaved: (bookId: number) =>
    drop({ keys: [cacheKeys.bookEvents(bookId)], prefixes: [cacheKeys.shelvesPrefix()] }),
};
