import { computed, ref, type Ref } from "vue";
import { reorderShelfItem } from "../api/books";
import type { Book, ShelfRef, ShelfReorderRequest } from "../api/types";

export interface ShelfOrderOptions {
  /** The shelf's books as shown. A move shows up here before it is saved. */
  books: Ref<Book[]>;
  /** Whether there are more books that are not yet loaded. */
  hasMore: Ref<boolean>;
  /** Positions are persisted against this shelf. */
  shelf: ShelfRef;
  /** Whether reordering is allowed (no search filter or page load in progress). */
  enabled: Ref<boolean>;
  /** Reconcile loaded pages with the server's order. */
  refresh: () => Promise<void>;
}

/**
 * Saves the order of books on one shelf, then reloads the shelf to match the server.
 */
export function useShelfOrder(options: ShelfOrderOptions) {
  const { books, hasMore, shelf, enabled, refresh } = options;

  const isSaving = ref(false);

  /**
   * Whether a book may be moved (reordered) right now.
   * A book cannot be moved while:
   * - a search filter is active on the shelf,
   * - more books are loading,
   * - the shelf shows an error, or
   * - an earlier move is still being saved.
   */
  const canReorder = computed(() => enabled.value && !isSaving.value);

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

  /** Saves the place of the book at `index` of `books`, where it was just moved, between its new neighbors. */
  async function saveBookAt(index: number) {
    if (!canReorder.value) {
      return;
    }

    const list = books.value;
    const movedBook = list[index];
    if (!movedBook) {
      return;
    }
    const beforeBook = index > 0 ? list[index - 1] : null;
    const afterBook = index < list.length - 1 ? list[index + 1] : null;

    await persist({
      moved_book_id: movedBook.id,
      book_id_before: beforeBook?.id ?? null,
      book_id_after: afterBook?.id ?? null,
    });
  }

  /** Moves a book to the top or bottom of the shelf. */
  async function moveBookToEdge(bookId: number, edge: "top" | "bottom") {
    if (!canReorder.value) {
      return;
    }

    const previousBooks = [...books.value];
    const bookToMove = previousBooks.find((book) => book.id === bookId);

    if (!bookToMove) {
      return;
    }

    const updatedBooks = previousBooks.filter((book) => book.id !== bookId);

    if (edge === "top") {
      updatedBooks.unshift(bookToMove);
    }

    // When hasMore is true, the bottom of the shelf is not actually the last book in the list.
    // In that case, we don't actually move the book as it wouldn't be loaded yet
    // (we just remove it from the list, as done above).
    else if (!hasMore.value) {
      updatedBooks.push(bookToMove);
    }
    books.value = updatedBooks;

    await persist({ moved_book_id: bookId, edge }, previousBooks);
  }

  return { isSaving, canReorder, saveBookAt, moveBookToEdge };
}
