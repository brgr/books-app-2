import { ref, type Ref } from "vue";
import { reorderShelfItem } from "../api/books";
import type { Book } from "../api/types";

export interface ShelfReorderOptions {
  /**
   * The very array being rendered: vuedraggable reorders it in place, and moving a book to an edge
   * splices it directly, so this has to be the same ref the shelf draws from.
   */
  books: Ref<Book[]>;
  /** Positions are persisted against this shelf; `null` (unresolved shelf) disables persisting. */
  shelfId: Ref<number | null>;
  /** Whether reordering is allowed at all. Normally off while the shelf shows only part of itself. */
  enabled: Ref<boolean>;
  /** Mirrors a persisted order back into the caller's accumulated items. */
  onPersisted: (order: Book[]) => Promise<void>;
}

/** How long after a drag a stray click from the same gesture can still land. */
const clickGraceMs = 200;

/**
 * Drag-to-reorder for one shelf: tracks the gesture, persists the new position, and reports when a
 * click is really the tail of a drag rather than a tap on a book.
 */
export function useShelfReorder(options: ShelfReorderOptions) {
  const { books, shelfId, enabled, onPersisted } = options;

  const isDragging = ref(false);
  const lastDragTime = ref(0);

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

  // Persists a reorder against the shelf, then mirrors the new order back into the accumulated
  // items so it survives future page loads
  async function persist(order: Book[], movedId: number, beforeId: number | null, afterId: number | null) {
    if (shelfId.value === null) return;

    try {
      await reorderShelfItem(shelfId.value, {
        moved_book_id: movedId,
        before_book_id: beforeId,
        after_book_id: afterId,
      });
      await onPersisted([...order]);
    } catch (err) {
      console.error("Failed to reorder books:", err);
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
    if (!enabled.value) {
      return;
    }

    const list = books.value;
    const movedBook = list[event.newIndex];
    if (!movedBook) return;
    const beforeBook = event.newIndex > 0 ? list[event.newIndex - 1] : null;
    const afterBook = event.newIndex < list.length - 1 ? list[event.newIndex + 1] : null;

    await persist(list, movedBook.id, beforeBook?.id ?? null, afterBook?.id ?? null);
  }

  /** Jumps a book to the top or bottom of the shelf, as the context menu offers. */
  async function moveBookToEdge(bookId: number, edge: "top" | "bottom") {
    if (!enabled.value) return;

    const list = books.value;
    const idx = list.findIndex((book) => book.id === bookId);
    const targetIndex = edge === "top" ? 0 : list.length - 1;
    if (idx === -1 || idx === targetIndex) return;

    const [moved] = list.splice(idx, 1);
    if (edge === "top") list.unshift(moved);
    else list.push(moved);

    const beforeBook = edge === "bottom" ? (list[list.length - 2] ?? null) : null;
    const afterBook = edge === "top" ? (list[1] ?? null) : null;

    await persist(list, moved.id, beforeBook?.id ?? null, afterBook?.id ?? null);
  }

  return { isDragging, dragOptions, ignoresClick, handleDragStart, handleDragEnd, moveBookToEdge };
}
