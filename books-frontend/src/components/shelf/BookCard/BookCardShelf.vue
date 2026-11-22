<script setup lang="ts">
import { computed } from "vue";
import { type Book, ReadingShelf } from "../../../api/types";
import { formatReadingDate } from "../../../utils/date";

const props = defineProps<{
  book: Book;
}>();

const shelf = computed(() => props.book.shelf);

const SHELF_LABELS: Record<ReadingShelf, string> = {
  [ReadingShelf.WANT_TO_READ]: "Want to read",
  [ReadingShelf.STARTED]: "Started",
  [ReadingShelf.PAUSED]: "Paused",
  [ReadingShelf.FINISHED]: "Finished",
  [ReadingShelf.ABANDONED]: "Abandoned",
};

const SHELF_COLORS: Record<ReadingShelf, string> = {
  [ReadingShelf.WANT_TO_READ]: "var(--color-primary)",
  [ReadingShelf.STARTED]: "var(--color-warning)",
  [ReadingShelf.PAUSED]: "var(--color-warning)",
  [ReadingShelf.FINISHED]: "var(--color-success)",
  [ReadingShelf.ABANDONED]: "var(--color-text-secondary)",
};

const shelfLabel = computed(() => (shelf.value ? SHELF_LABELS[shelf.value] : "N/A"));
const shelfColor = computed(() => (shelf.value ? SHELF_COLORS[shelf.value] : "var(--color-text-secondary)"));
</script>

<template>
  <div class="book-shelf">
    <span class="book-shelf-label">Shelf:</span>
    <span class="book-shelf-pill" :style="{ borderColor: shelfColor, color: shelfColor }">
      {{ shelfLabel }}
    </span>
  </div>

  <div class="book-dates text-small text-muted">
    <div v-if="book.started_at">Started: {{ formatReadingDate(book.started_at) }}</div>
    <div v-if="book.finished_at">Finished: {{ formatReadingDate(book.finished_at) }}</div>
    <div v-if="book.progress?.unit === 'percent'">Progress: {{ book.progress.value }}%</div>
    <div v-else-if="book.progress">
      Progress: {{ book.progress.value }}
      <span v-if="book.page_count">/ {{ book.page_count }}</span>
    </div>
  </div>
</template>

<style scoped>
.book-shelf {
  margin-bottom: var(--spacing-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.book-shelf-label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.book-shelf-pill {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 600;
}

.book-dates {
  padding-top: var(--spacing-sm);
  display: flex;
  gap: var(--spacing-md);
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .book-shelf {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
