<script setup lang="ts">
import { computed } from "vue";
import { type Book, ReadingShelf } from "../../api/types";
import { formatReadingDate } from "../../utils/date";
import BookReadingCard from "./BookReadingCard/BookReadingCard.vue";
import type { ReadingProgress } from "./BookReadingCard/types";
import BookShelfButton from "./BookShelfButton/BookShelfButton.vue";

/**
 * Where the user is with a book: the reading card with progress while they are reading it, and otherwise the button to
 * move it to another shelf along with the dates they read it.
 */
const props = defineProps<{
  book: Book;
}>();

const reading = computed(() => props.book.shelf === ReadingShelf.STARTED);

// A book without recorded progress starts at zero, counted in pages when we know how many it has
const progress = computed<ReadingProgress>(
  () => props.book.progress ?? { unit: props.book.page_count != null ? "page" : "percent", value: 0 },
);
</script>

<template>
  <div class="book-shelf-section">
    <BookReadingCard
      v-if="reading"
      :book-id="book.id"
      :shelf="book.shelf"
      :progress="progress"
      :page-count="book.page_count"
      :started-at="book.started_at"
      :finished-at="book.finished_at"
    />

    <BookShelfButton v-else :book-id="book.id" :shelf="book.shelf" />
  </div>

  <div v-if="!reading" class="book-dates">
    <div v-if="book.started_at" class="date-item">
      <strong>Started:</strong> {{ formatReadingDate(book.started_at) }}
    </div>
    <div v-if="book.finished_at" class="date-item">
      <strong>Finished:</strong> {{ formatReadingDate(book.finished_at) }}
    </div>
  </div>
</template>

<style scoped>
.book-shelf-section {
  margin-bottom: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.book-dates {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.date-item {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.date-item strong {
  color: var(--color-text);
}

@media (max-width: 768px) {
  .book-shelf-section {
    align-items: center;
  }
}
</style>
