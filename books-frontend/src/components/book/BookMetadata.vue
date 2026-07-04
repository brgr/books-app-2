<script setup lang="ts">
import type {Book} from '../../api/types'
import {formatShortDate} from '../../utils/date'

defineProps<{
  book: Book
}>()
</script>

<template>
  <div class="book-metadata">
    <h2>Book Details</h2>
    <div class="metadata-grid">
      <div v-if="book.isbn" class="metadata-item">
        <strong>ISBN:</strong> {{ book.isbn }}
      </div>
      <div v-if="book.page_count" class="metadata-item">
        <strong>Pages:</strong> {{ book.page_count }}
      </div>
      <div v-if="book.published_date" class="metadata-item">
        <strong>Published:</strong> {{ formatShortDate(book.published_date) }}
      </div>
      <div class="metadata-item">
        <strong>Added:</strong> {{ formatShortDate(book.created_at) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-metadata h2 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: var(--spacing-md);
  width: 100%;
}

.metadata-item {
  font-size: 14px;
  color: var(--color-text-secondary);
  min-width: 0;
  word-break: break-word;
  overflow-wrap: anywhere;
}

.metadata-item strong {
  color: var(--color-text);
}

@media (max-width: 768px) {
  .metadata-grid {
    grid-template-columns: 1fr;
  }
}
</style>
