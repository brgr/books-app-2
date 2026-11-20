import { ref, type Ref } from "vue";
import { reorderShelfItem } from "../api/books";
import type { Book, ShelfRef, ShelfReorderRequest } from "../api/types";

export interface ShelfOrderOptions {
  /** The shelf's books as shown. A move shows up here before it is saved. */
  books: Ref<Book[]>;
  /** Positions are persisted against this shelf. */
  shelf: ShelfRef;
  /** Reconcile loaded pages with the server's order. */
  refresh: () => Promise<void>;
}

/**
 * Saves the order of books on one shelf, then reloads the shelf to match the server.
 */
export function useShelfOrder(options: ShelfOrderOptions) {
  const { books, shelf, refresh } = options;

  const isSaving = ref(false);

  /**
   * Persists changes to the shelf and updates the order of books based on the provided payload.
   * On failure, it restores the previous order of books if provided.
   */
  async function persist(payload: ShelfReorderRequest, booksToRestoreOnFailure?: Book[]) {
    isSaving.value = true;

    try {
      await reorderShelfItem(shelf, payload);
    } catch (err) {
      if (booksToRestoreOnFailure) {
        books.value = booksToRestoreOnFailure;
      }

      console.error("Failed to reorder books:", err);
    }

    try {
      await refresh();
    } catch (err) {
      console.error("Failed to refresh shelf:", err);
    } finally {
      isSaving.value = false;
    }
  }

  return { isSaving, persist };
}
