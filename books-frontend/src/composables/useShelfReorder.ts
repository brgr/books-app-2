import { ref, type Ref } from "vue";
import { reorderShelfItem } from "../api/books";
import type { Book, ShelfRef, ShelfReorderRequest } from "../api/types";

export interface ShelfReorderOptions {
  /**
   * The very array being rendered: vuedraggable reorders it in place.
   */
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

/** How long after a drag a stray click from the same gesture can still land. */
const clickGraceMs = 200;

/**
 * Drag-to-reorder for one shelf: tracks the gesture, persists the new position, and reports when a
 * click is really the tail of a drag rather than a tap on a book.
 */
export function useShelfReorder(options: ShelfReorderOptions) {
  const { books, hasMore, shelf, enabled, refresh } = options;

  const isDragging = ref(false);
  const lastDragTime = ref(0);
  const isSaving = ref(false);
  const message = ref("");
  const error = ref("");

  const dragOptions = {
    animation: 150,
    delay: 120,
    "delay-on-touch-only": true,
    "ghost-class": "grid-ghost",
    "drag-class": "grid-drag",
    "chosen-class": "grid-chosen",
  };

  /**
   * True while a drag is in flight or has only just ended, when the click closing the gesture would
   * otherwise open the book that was moved.
   */
  function ignoresClick() {
    return isDragging.value || Date.now() - lastDragTime.value < clickGraceMs;
  }

  /**
   * Persists changes to the shelf and updates the order of books based on the provided payload.
   * On failure, it restores the previous order of books if provided.
   */
  async function persist(payload: ShelfReorderRequest, booksToRestoreOnFailure?: Book[]) {
    isSaving.value = true;
    message.value = "";
    error.value = "";

    try {
      await reorderShelfItem(shelf, payload);
    } catch (err) {
      if (booksToRestoreOnFailure) {
        books.value = booksToRestoreOnFailure;
      }

      console.error("Failed to reorder books:", err);
      error.value = "Could not move the book. Please try again.";
    }

    try {
      await refresh();

      if (!error.value) {
        message.value = payload.edge ? `Moved to ${payload.edge}.` : "Book order updated.";
      }
    } catch (err) {
      console.error("Failed to refresh shelf:", err);
      error.value = "Could not refresh the shelf. Reload before moving more books.";
    } finally {
      isSaving.value = false;
    }
  }

  function handleDragStart() {
    isDragging.value = true;
  }

  async function handleDragEnd(event: { newIndex?: number; oldIndex?: number } | null) {
    isDragging.value = false;
    lastDragTime.value = Date.now();

    if (!event || event.newIndex === undefined || event.oldIndex === undefined) {
      return;
    }
    if (event.newIndex === event.oldIndex) {
      return;
    }
    if (!enabled.value || isSaving.value) {
      return;
    }

    const list = books.value;
    const movedBook = list[event.newIndex];
    if (!movedBook) {
      return;
    }
    const beforeBook = event.newIndex > 0 ? list[event.newIndex - 1] : null;
    const afterBook = event.newIndex < list.length - 1 ? list[event.newIndex + 1] : null;

    await persist({
      moved_book_id: movedBook.id,
      book_id_before: beforeBook?.id ?? null,
      book_id_after: afterBook?.id ?? null,
    });
  }

  /** Moves a book to the top or bottom of the shelf. */
  async function moveBookToEdge(bookId: number, edge: "top" | "bottom") {
    if (!enabled.value || isSaving.value) {
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

  return {
    isDragging,
    isSaving,
    message,
    error,
    dragOptions,
    ignoresClick,
    handleDragStart,
    handleDragEnd,
    moveBookToEdge,
  };
}
