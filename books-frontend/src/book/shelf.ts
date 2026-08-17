import { ReadingShelf } from "../api/types";

const SHELF_LABELS: Record<ReadingShelf, string> = {
  [ReadingShelf.WANT_TO_READ]: "Want to read",
  [ReadingShelf.STARTED]: "Started",
  [ReadingShelf.FINISHED]: "Finished",
  [ReadingShelf.ABANDONED]: "Abandoned",
};

const SHELF_COLORS: Record<ReadingShelf, string> = {
  [ReadingShelf.WANT_TO_READ]: "var(--color-primary)",
  [ReadingShelf.STARTED]: "var(--color-warning)",
  [ReadingShelf.FINISHED]: "var(--color-success)",
  [ReadingShelf.ABANDONED]: "var(--color-text-secondary)",
};

export function getShelfLabel(shelf: ReadingShelf | null): string {
  return shelf ? SHELF_LABELS[shelf] : "N/A";
}

export function getShelfColor(shelf: ReadingShelf | null): string {
  return shelf ? SHELF_COLORS[shelf] : "var(--color-text-secondary)";
}
