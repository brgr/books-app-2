import { computed, onBeforeUnmount, ref, type Ref } from "vue";
import { reorderShelfItem } from "../api/books";
import type { Book, ShelfRef, ShelfReorderRequest } from "../api/types";
import { LONG_PRESS_MOVE_THRESHOLD, LONG_PRESS_MS } from "./useContextMenu";

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
  /** A finger rested on a book long enough to pick it up; `rect` is where the book sits on screen. */
  onHold: (bookId: number, rect: DOMRect) => void;
}

/** The parts of a SortableJS `choose` event used here. */
interface ChooseEvent {
  item: HTMLElement;
  oldIndex?: number;
  originalEvent?: Event;
}

/**
 * How long clicks are ignored after a drag or a long press ends. Letting go sends a click of its own, which would
 * otherwise open the book.
 */
const clickGraceMs = 200;

/**
 * How far, in CSS pixels, a finger holding a book must move from where it first touched before the book starts to
 * drag. It is more than the hold itself allows: a finger that crept a little during the hold still has room to wobble.
 */
const dragStartDistance = LONG_PRESS_MOVE_THRESHOLD + 6;

function isTouch(event: Event | undefined) {
  if (!event) {
    return false;
  }
  return "pointerType" in event ? event.pointerType === "touch" : "touches" in event;
}

function preventDefault(event: Event) {
  if (event.cancelable) {
    event.preventDefault();
  }
}

/**
 * Drag-to-reorder for one shelf: tracks the gesture, persists the new position, and reports when a
 * click is really the tail of a drag rather than a tap on a book.
 *
 * On touch, holding a book opens its menu and lets it be dragged. SortableJS's drag delay decides when the hold has
 * lasted long enough, for both.
 */
export function useShelfReorder(options: ShelfReorderOptions) {
  const { books, hasMore, shelf, enabled, refresh, onHold } = options;

  const isDragging = ref(false);
  const lastGestureEnd = ref(0);
  const isSaving = ref(false);

  const canDrag = computed(() => enabled.value && !isSaving.value);

  const dragOptions = computed(() => ({
    animation: 150,
    delay: LONG_PRESS_MS,
    "delay-on-touch-only": true,
    "touch-start-threshold": LONG_PRESS_MOVE_THRESHOLD,
    // SortableJS's own pointer-driven drag everywhere (phones get it anyway), as the browser's drag and drop would
    // ignore the tolerance below
    "force-fallback": true,
    // On a shelf that can't be reordered, a held book never starts dragging. Disabling SortableJS instead would also
    // take away the long press that opens the book's menu
    "fallback-tolerance": canDrag.value ? dragStartDistance : Infinity,
    "ghost-class": "grid-ghost",
    "drag-class": "grid-drag",
  }));

  /**
   * True while a drag is in flight or a drag or long press has only just ended, when the click closing the gesture
   * would otherwise open the book.
   */
  function ignoresClick() {
    return isDragging.value || Date.now() - lastGestureEnd.value < clickGraceMs;
  }

  /**
   * SortableJS chose a book. With a touch, that means the long press completed: the book is picked up until the finger
   * lifts. With the mouse, it happens on every button press, which is no hold at all.
   */
  function handleChoose(event: ChooseEvent) {
    if (!isTouch(event.originalEvent)) {
      return;
    }

    const book = event.oldIndex === undefined ? undefined : books.value[event.oldIndex];
    if (!book) {
      return;
    }

    // While the book is picked up, the finger moves the book (but not the page)
    document.addEventListener("touchmove", preventDefault, { passive: false });
    document.addEventListener("touchend", endHold, { passive: false });
    document.addEventListener("touchcancel", endHold);

    onHold(book.id, event.item.getBoundingClientRect());
  }

  function endHold(event: TouchEvent) {
    if (event.touches.length > 0) {
      return;
    }

    // Lifting the finger would otherwise click whatever is under it now: the menu's backdrop, or the book
    preventDefault(event);
    lastGestureEnd.value = Date.now();
    stopHoldListeners();
  }

  function stopHoldListeners() {
    document.removeEventListener("touchmove", preventDefault);
    document.removeEventListener("touchend", endHold);
    document.removeEventListener("touchcancel", endHold);
  }

  onBeforeUnmount(stopHoldListeners);

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

  function handleDragStart() {
    isDragging.value = true;
  }

  async function handleDragEnd(event: { newIndex?: number; oldIndex?: number } | null) {
    isDragging.value = false;
    lastGestureEnd.value = Date.now();

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
    dragOptions,
    ignoresClick,
    handleChoose,
    handleDragStart,
    handleDragEnd,
    moveBookToEdge,
  };
}
