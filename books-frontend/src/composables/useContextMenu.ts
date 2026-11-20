import { ref } from "vue";

/** What a menu is attached to. Its value is the position on screen of the book the menu belongs to. */
export interface MenuAnchor {
  top: number;
  left: number;
  width: number;
  height: number;
}

interface ContextMenuState {
  x: number;
  y: number;
  /** The book the menu is open for; null while the menu is closed. */
  bookId: number | null;
  /** Set when a long press picked the book up: the menu then sits beside the book instead of at `x`/`y`. */
  anchor: MenuAnchor | null;
}

/**
 * Tracks the position and target of a right-click / long-press context menu.
 * `open` records where the menu was invoked and which book it targets; `close`
 * hides it by clearing the target.
 */
export function useContextMenu() {
  const contextMenu = ref<ContextMenuState>({ x: 0, y: 0, bookId: null, anchor: null });

  function openContextMenu(payload: { bookId: number; x: number; y: number; anchor?: MenuAnchor }) {
    contextMenu.value = {
      x: payload.x,
      y: payload.y,
      bookId: payload.bookId,
      anchor: payload.anchor ?? null,
    };
  }

  function closeContextMenu() {
    contextMenu.value.bookId = null;
    contextMenu.value.anchor = null;
  }

  return { contextMenu, openContextMenu, closeContextMenu };
}
