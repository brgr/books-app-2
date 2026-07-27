<script setup lang="ts">
import { computed } from "vue";
import { type Book } from "../../../api/types";
import { formatShortDate } from "../../../utils/date";
import { getShelfColor, getShelfLabel } from "../../../book/shelf";

const props = defineProps<{
  book: Book;
}>();

const shelf = computed(() => props.book.user_book?.shelf || null);
</script>

<template>
  <div v-if="shelf" class="book-shelf">
    <span class="book-shelf-label">Shelf:</span>
    <span class="book-shelf-pill" :style="{ borderColor: getShelfColor(shelf), color: getShelfColor(shelf) }">
      {{ getShelfLabel(shelf) }}
    </span>
  </div>

  <div v-if="book.user_book" class="book-dates text-small text-muted">
    <div v-if="book.user_book.started_at">Started: {{ formatShortDate(book.user_book.started_at) }}</div>
    <div v-if="book.user_book.finished_at">Finished: {{ formatShortDate(book.user_book.finished_at) }}</div>
    <div v-if="book.user_book.current_percent !== null">Progress: {{ book.user_book.current_percent }}%</div>
    <div v-else-if="book.user_book.current_page !== null">
      Progress: {{ book.user_book.current_page }}
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
