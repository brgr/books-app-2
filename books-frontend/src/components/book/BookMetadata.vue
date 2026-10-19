<script setup lang="ts">
import { computed } from "vue";
import type { Book } from "../../api/types";
import { formatShortDate } from "../../utils/date";

const props = defineProps<{
  book: Book;
}>();

const amazonUrl = computed(() => {
  const isbn = props.book.isbn?.replace(/[\s-]/g, "");
  const query = isbn || [props.book.title, props.book.author].filter(Boolean).join(" ");
  return `https://www.amazon.it/s?${new URLSearchParams({ k: query })}`;
});

const googleBooksUrl = computed(() => {
  if (props.book.google_books_id) {
    return `https://books.google.com/books?${new URLSearchParams({ id: props.book.google_books_id })}`;
  }

  const isbn = props.book.isbn?.replace(/[\s-]/g, "");
  const query = isbn ? `isbn:${isbn}` : [props.book.title, props.book.author].filter(Boolean).join(" ");
  return `https://books.google.com/books?${new URLSearchParams({ q: query })}`;
});
</script>

<template>
  <div class="book-metadata">
    <h2>Book Details</h2>
    <div class="metadata-grid">
      <div v-if="book.isbn" class="metadata-item"><strong>ISBN:</strong> {{ book.isbn }}</div>
      <div v-if="book.page_count" class="metadata-item"><strong>Pages:</strong> {{ book.page_count }}</div>
      <div v-if="book.published_date" class="metadata-item">
        <strong>Published:</strong> {{ formatShortDate(book.published_date) }}
      </div>
      <div class="metadata-item"><strong>Added:</strong> {{ formatShortDate(book.created_at) }}</div>
      <div class="metadata-item">
        <a :href="googleBooksUrl" target="_blank" rel="noopener noreferrer">
          {{ book.google_books_id ? "View on Google Books" : "Search on Google Books" }}
        </a>
      </div>
      <div class="metadata-item">
        <a :href="amazonUrl" target="_blank" rel="noopener noreferrer">Search on Amazon.it</a>
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
