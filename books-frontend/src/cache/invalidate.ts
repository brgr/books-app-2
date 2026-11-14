import type { QueryKey } from "@tanstack/vue-query";
import { queryClient } from "../query/client";
import { queryKeys } from "../query/keys";
import { cacheKeys } from "./keys";
import { cacheDel, cacheInvalidateByPrefix } from "./store";

interface Targets {
  /** Exact keys to drop. */
  keys?: string[];
  /** Key prefixes to drop, covering every entry below them (e.g. all cached pages of a shelf). */
  prefixes?: string[];
  /** TanStack Query keys to invalidate, for the data that has already moved there. */
  queries?: QueryKey[];
}

async function drop(targets: Targets): Promise<void> {
  await Promise.all([...(targets.keys ?? []).map(cacheDel), ...(targets.prefixes ?? []).map(cacheInvalidateByPrefix)]);

  for (const queryKey of targets.queries ?? []) {
    void queryClient.invalidateQueries({ queryKey });
  }
}

/**
 * What each change makes stale.
 *
 * Callers name the change they just performed and this decides which entries go.
 */
export const invalidateCache = {
  bookAdded: () => drop({ prefixes: [cacheKeys.shelvesPrefix()], queries: [queryKeys.shelves.all()] }),

  bookUpdated: (bookId: number) =>
    drop({
      keys: [cacheKeys.book(bookId)],
      prefixes: [cacheKeys.shelvesPrefix()],
      queries: [queryKeys.shelves.all(), queryKeys.book.detail(bookId)],
    }),

  bookDeleted: (bookId: number) =>
    drop({
      keys: [cacheKeys.book(bookId), cacheKeys.bookEvents(bookId)],
      prefixes: [cacheKeys.shelvesPrefix()],
      queries: [queryKeys.shelves.all(), queryKeys.book.customShelves(bookId)],
    }),

  shelfChanged: (bookId: number) =>
    drop({
      keys: [cacheKeys.book(bookId), cacheKeys.bookEvents(bookId)],
      prefixes: [cacheKeys.shelvesPrefix()],
      queries: [
        queryKeys.shelves.all(),
        queryKeys.book.detail(bookId),
        queryKeys.book.events(bookId),
        queryKeys.book.customShelves(bookId),
      ],
    }),

  // The book itself is written directly into the cache, but the timeline is not; it's not really possible
  // to know what the timeline will look like after a note is added (only the server knows its datetime, for example),
  // so we just drop it and let it be refetched.
  notesSaved: (bookId: number) =>
    drop({ keys: [cacheKeys.bookEvents(bookId)], queries: [queryKeys.book.events(bookId)] }),

  // Shelf tiles render the reading progress, so their cached pages go stale along with the timeline.
  progressSaved: (bookId: number) =>
    drop({
      keys: [cacheKeys.bookEvents(bookId)],
      prefixes: [cacheKeys.shelvesPrefix()],
      queries: [queryKeys.shelves.all(), queryKeys.book.events(bookId)],
    }),

  ratingSaved: (bookId: number) =>
    drop({
      keys: [cacheKeys.bookEvents(bookId)],
      prefixes: [cacheKeys.shelvesPrefix()],
      queries: [queryKeys.shelves.all(), queryKeys.book.events(bookId)],
    }),
};
