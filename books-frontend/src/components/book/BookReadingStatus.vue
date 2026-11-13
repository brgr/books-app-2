<script setup lang="ts">
import { computed } from "vue";
import { type BookProgressUpdate, type ReadingDateValue, ReadingShelf, type UserBook } from "../../api/types";
import { formatReadingDate } from "../../utils/date";
import BookReadingCard from "./BookReadingCard/BookReadingCard.vue";
import type { ReadingProgress } from "./BookReadingCard/types";
import BookShelfButton from "./BookShelfButton/BookShelfButton.vue";

/**
 * Where the user is with a book: the reading card with progress while they are reading it, and otherwise the button to
 * move it to another shelf along with the dates they read it.
 */
const props = defineProps<{
  userBook: UserBook;
  pageCount: number | null;
  savingShelf: boolean;
  savingProgress: boolean;
}>();

const emit = defineEmits<{
  change: [shelf: ReadingShelf, readingDate?: ReadingDateValue];
  "update-progress": [progress: BookProgressUpdate];
}>();

const reading = computed(() => props.userBook.shelf === ReadingShelf.STARTED);

// A book without recorded progress starts at zero, counted in pages when we know how many it has
const progress = computed<ReadingProgress>(
  () => props.userBook.progress ?? { unit: props.pageCount != null ? "page" : "percent", value: 0 },
);
</script>

<template>
  <div class="book-shelf-section">
    <BookReadingCard
      v-if="reading"
      :shelf="userBook.shelf"
      :updating="savingShelf"
      :progress="progress"
      :page-count="pageCount"
      :started-at="userBook.started_at"
      :finished-at="userBook.finished_at"
      :progress-saving="savingProgress"
      @change="(shelf, readingDate) => emit('change', shelf, readingDate)"
      @update-progress="(update) => emit('update-progress', update)"
    />

    <BookShelfButton
      v-else
      :shelf="userBook.shelf"
      :updating="savingShelf"
      @change="(shelf, readingDate) => emit('change', shelf, readingDate)"
    />
  </div>

  <div v-if="!reading" class="book-dates">
    <div v-if="userBook.started_at" class="date-item">
      <strong>Started:</strong> {{ formatReadingDate(userBook.started_at) }}
    </div>
    <div v-if="userBook.finished_at" class="date-item">
      <strong>Finished:</strong> {{ formatReadingDate(userBook.finished_at) }}
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
