<script setup lang="ts">
import { type Book } from '../../../api/types'
import { formatShortDate } from '../../../utils/date'

defineProps<{
  book: Book
}>()
</script>

<template>
  <div class="book-meta">
    <span v-if="book.isbn" class="meta-item">
      <strong>ISBN:</strong> {{ book.isbn }}
    </span>
    <span v-if="book.page_count" class="meta-item">
      <strong>Pages:</strong> {{ book.page_count }}
    </span>
    <span v-if="book.published_date" class="meta-item">
      <strong>Published:</strong> {{ formatShortDate(book.published_date) }}
    </span>
  </div>
</template>

<style scoped>
.book-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border);
}

.meta-item {
  font-size: 12px;
  color: var(--color-text-secondary);
  word-break: break-word;
  overflow-wrap: anywhere;
}

.meta-item strong {
  color: var(--color-text);
}
</style>
