import { computed, onBeforeUnmount, ref, type Ref } from "vue";
import type { Book } from "../../api/types";
import { swallowNextClick } from "../../utils/click";

export interface ShelfDragOptions {
  /**
   * The very array being rendered: vuedraggable reorders it in place.
   */
  books: Ref<Book[]>;
  /** Whether a picked-up book may be dragged. It can still be picked up when not. */
  canDrag: Ref<boolean>;
  /** A finger rested on a book long enough to pick it up; `rect` is where the book sits on screen. */
  onPickUp: (bookId: number, rect: DOMRect) => void;
  /** A book starts being dragged. */
  onDragStart: () => void;
  /** A book was dropped at `index` of `books`, away from where it was. */
  onDrop: (index: number) => void;
}

/** The parts of a SortableJS `choose` event used here. */
interface ChooseEvent {
  item: HTMLElement;
  oldIndex?: number;
  originalEvent?: Event;
}

/**
 * How long a finger must rest on a book before the touch stops being a tap or a scroll. After this, the book is picked up:
 * its context menu opens, and moving on drags the book.
 */
const longPressMs = 350;

/**
 * How far, in CSS pixels, a resting finger may wander during the hold and still count as a long press.
 */
const longPressMoveThreshold = 10;

/**
 * How far, in CSS pixels, a finger holding a book must move from where it first touched before the book starts to
 * drag. It is more than the hold itself allows: a finger that crept a little during the hold still has room to wobble.
 */
const dragStartDistance = longPressMoveThreshold + 6;

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
 * Reports when a book is picked up and where it is dropped.
 * It also swallows the click that letting go of such a book sends. Such a click must not open the book.
 *
 * On touch, holding a book picks it up, and moving drags it.
 * For both, SortableJS's drag delay decides when the hold has lasted long enough.
 */
export function useShelfDrag(options: ShelfDragOptions) {
  const { books, canDrag, onPickUp, onDragStart, onDrop } = options;

  const isDragging = ref(false);

  const dragOptions = computed(() => ({
    animation: 150,
    delay: longPressMs,
    "delay-on-touch-only": true,
    "touch-start-threshold": longPressMoveThreshold,
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

    onPickUp(book.id, event.item.getBoundingClientRect());
  }

  function endHold(event: TouchEvent) {
    if (event.touches.length > 0) {
      return;
    }

    // Lifting the finger would otherwise click whatever is under it now: the menu's backdrop, or the book
    preventDefault(event);
    swallowNextClick();
    stopHoldListeners();
  }

  function stopHoldListeners() {
    document.removeEventListener("touchmove", preventDefault);
    document.removeEventListener("touchend", endHold);
    document.removeEventListener("touchcancel", endHold);
  }

  onBeforeUnmount(stopHoldListeners);

  function handleDragStart() {
    isDragging.value = true;
    onDragStart();
  }

  function handleDragEnd(event: { newIndex?: number; oldIndex?: number } | null) {
    isDragging.value = false;
    swallowNextClick();

    if (!event || event.newIndex === undefined || event.oldIndex === undefined) {
      return;
    }
    if (event.newIndex === event.oldIndex) {
      return;
    }

    onDrop(event.newIndex);
  }

  return { isDragging, dragOptions, handleChoose, handleDragStart, handleDragEnd };
}
