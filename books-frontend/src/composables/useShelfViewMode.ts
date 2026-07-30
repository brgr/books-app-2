import { ref, watch, type Ref } from "vue";
import type { ShelfName } from "../api/types";

// TODO: At one point, we should move this in the backend, so that it persists across devices.

export type ViewMode = "list" | "grid";

const storageKey = (shelf: ShelfName) => `shelfViewMode:${shelf}`;

function readStored(shelf: ShelfName): ViewMode | null {
  const stored = localStorage.getItem(storageKey(shelf));
  return stored === "list" || stored === "grid" ? stored : null;
}

/**
 * One shelf's list/grid mode, remembered across reloads. Each shelf keeps its own, so a page can
 * show "Reading now" as a list next to "Want to read" as a grid.
 */
export function useShelfViewMode(shelf: ShelfName, fallback: ViewMode = "list"): Ref<ViewMode> {
  const viewMode = ref<ViewMode>(readStored(shelf) ?? fallback);

  watch(viewMode, (mode) => {
    localStorage.setItem(storageKey(shelf), mode);
  });

  return viewMode;
}
