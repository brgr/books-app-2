import { ref } from "vue";

/**
 * How long a finger must rest on a book before the touch stops being a tap or a scroll. After this, releasing without
 * moving opens the context menu and moving drags the book.
 */
export const LONG_PRESS_MS = 350;

/**
 * How far, in CSS pixels, a resting finger may wander during the hold and still count as a long press.
 */
export const LONG_PRESS_MOVE_THRESHOLD = 10;

interface ContextMenuState {
  visible: boolean;
  x: number;
  y: number;
  bookId: number | null;
}

/**
 * Tracks the position and target of a right-click / long-press context menu.
 * `open` records where the menu was invoked and which book it targets; `close`
 * hides it and clears the target.
 */
export function useContextMenu() {
  const contextMenu = ref<ContextMenuState>({ visible: false, x: 0, y: 0, bookId: null });

  function openContextMenu(payload: { bookId: number; x: number; y: number }) {
    contextMenu.value = { visible: true, x: payload.x, y: payload.y, bookId: payload.bookId };
  }

  function closeContextMenu() {
    contextMenu.value.visible = false;
    contextMenu.value.bookId = null;
  }

  return { contextMenu, openContextMenu, closeContextMenu };
}
