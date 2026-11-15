import type { QueryKey } from "@tanstack/vue-query";
import { queryClient } from "./client";
import { queryKeys } from "./keys";

function invalidate(...keys: QueryKey[]) {
  for (const queryKey of keys) {
    void queryClient.invalidateQueries({ queryKey });
  }
}

/**
 * Cache invalidation, keyed by the change that was just performed.
 */
export const invalidateAfter = {
  bookAdded: () => invalidate(queryKeys.shelves.all()),
  bookUpdated: (bookId: number) => invalidate(queryKeys.shelves.all(), queryKeys.book.detail(bookId)),
  bookDeleted: (bookId: number) => {
    // There is nothing left to refetch for the book itself
    queryClient.removeQueries({ queryKey: queryKeys.book.all(bookId) });
    invalidate(queryKeys.shelves.all());
  },
  allBooksDeleted: () => {
    queryClient.removeQueries({ queryKey: queryKeys.book.root() });
    invalidate(queryKeys.shelves.all());
  },
  // An import can potentially touch any book and shelf
  readingListImported: () => invalidate(queryKeys.shelves.all(), queryKeys.book.root()),
  shelfChanged: (bookId: number) => invalidate(queryKeys.shelves.all(), queryKeys.book.all(bookId)),
  notesSaved: (bookId: number) => invalidate(queryKeys.book.events(bookId)),
  // Shelf tiles render the reading progress, so the shelves go stale along with the timeline
  progressSaved: (bookId: number) => invalidate(queryKeys.shelves.all(), queryKeys.book.events(bookId)),
  ratingSaved: (bookId: number) => invalidate(queryKeys.shelves.all(), queryKeys.book.events(bookId)),
};
