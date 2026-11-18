import { ref } from "vue";

/**
 * How long a finger must rest on a book before the touch stops being a tap or a scroll. After this, the book is picked up:
 * its context menu opens, and moving on drags the book.
 */
export const LONG_PRESS_MS = 350;

/**
 * How far, in CSS pixels, a resting finger may wander during the hold and still count as a long press.
 */
export const LONG_PRESS_MOVE_THRESHOLD = 10;

/** What a menu is attached to. Its value is the position on screen of the book the menu belongs to. */
export interface MenuAnchor {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  bookId: number | null;
  /** Set when a long press picked the book up: the menu then sits beside the book instead of at `x`/`y`. */
  anchor: MenuAnchor | null;
}

/**
 * Tracks the position and target of a right-click / long-press context menu.
 * `open` records where the menu was invoked and which book it targets; `close`
 * hides it and clears the target.
 */
export function useContextMenu() {
  const contextMenu = ref<ContextMenuState>({ visible: false, x: 0, y: 0, bookId: null, anchor: null });

  function openContextMenu(payload: { bookId: number; x: number; y: number; anchor?: MenuAnchor }) {
    contextMenu.value = {
      visible: true,
      x: payload.x,
      y: payload.y,
      bookId: payload.bookId,
      anchor: payload.anchor ?? null,
    };
  }

  function closeContextMenu() {
    contextMenu.value.visible = false;
    contextMenu.value.bookId = null;
    contextMenu.value.anchor = null;
  }

  return { contextMenu, openContextMenu, closeContextMenu };
}
