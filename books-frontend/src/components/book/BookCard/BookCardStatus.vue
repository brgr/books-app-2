<script setup lang="ts">
import { computed } from 'vue'
import { type Book } from '../../../api/types'
import { formatShortDate } from '../../../utils/date'
import { getStatusColor, getStatusLabel } from '../../../book/status'

const props = defineProps<{
  book: Book
}>()

const readingStatus = computed(() => props.book.user_status?.status || null)
</script>

<template>
  <div v-if="readingStatus" class="book-status">
    <span class="book-status-label">Reading status:</span>
    <span
      class="book-status-pill"
      :style="{ borderColor: getStatusColor(readingStatus), color: getStatusColor(readingStatus) }"
    >
      {{ getStatusLabel(readingStatus) }}
    </span>
  </div>

  <div v-if="book.user_status" class="book-dates text-small text-muted">
    <div v-if="book.user_status.started_at">
      Started: {{ formatShortDate(book.user_status.started_at) }}
    </div>
    <div v-if="book.user_status.finished_at">
      Finished: {{ formatShortDate(book.user_status.finished_at) }}
    </div>
    <div v-if="book.user_status.current_page !== null">
      Progress: {{ book.user_status.current_page }}
      <span v-if="book.page_count">/ {{ book.page_count }}</span>
    </div>
  </div>
</template>

<style scoped>
.book-status {
  margin-bottom: var(--spacing-sm);
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.book-status-label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.book-status-pill {
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
  .book-status {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
