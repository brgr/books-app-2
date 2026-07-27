import { ShelfName } from "../api/types";

const SHELF_LABELS: Record<ShelfName, string> = {
  [ShelfName.WANT_TO_READ]: "Want to read",
  [ShelfName.STARTED]: "Started",
  [ShelfName.FINISHED]: "Finished",
  [ShelfName.ABANDONED]: "Abandoned",
};

const SHELF_COLORS: Record<ShelfName, string> = {
  [ShelfName.WANT_TO_READ]: "var(--color-primary)",
  [ShelfName.STARTED]: "var(--color-warning)",
  [ShelfName.FINISHED]: "var(--color-success)",
  [ShelfName.ABANDONED]: "var(--color-text-secondary)",
};

export function getShelfLabel(shelf: ShelfName | null): string {
  return shelf ? SHELF_LABELS[shelf] : "N/A";
}

export function getShelfColor(shelf: ShelfName | null): string {
  return shelf ? SHELF_COLORS[shelf] : "var(--color-text-secondary)";
}
