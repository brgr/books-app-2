import { ref } from "vue";

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
