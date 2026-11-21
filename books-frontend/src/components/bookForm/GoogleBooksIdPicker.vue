<script setup lang="ts">
import { isAxiosError } from "axios";
import { computed, ref } from "vue";
import { searchGoogleBooks } from "../../api/books";
import type { GoogleBookResult } from "../../api/types";

const props = defineProps<{
  title: string;
  author: string;
  isbn: string;
}>();

const emit = defineEmits<{
  select: [googleBooksId: string];
}>();

type GoogleBooksMatch = GoogleBookResult & { google_books_id: string };

const results = ref<GoogleBooksMatch[]>([]);
const loading = ref(false);
const error = ref("");
const hasSearched = ref(false);

const query = computed(() => {
  const isbn = props.isbn.replace(/[\s-]/g, "");
  return isbn ? `isbn:${isbn}` : [props.title, props.author].join(" ").trim();
});

async function handleSearch() {
  error.value = "";
  loading.value = true;
  try {
    const found = await searchGoogleBooks(query.value);
    results.value = found.filter((result): result is GoogleBooksMatch => !!result.google_books_id);
    hasSearched.value = true;
  } catch (err) {
    console.error("Google Books search failed:", err);
    const detail = isAxiosError<{ detail?: unknown }>(err) ? err.response?.data?.detail : undefined;
    error.value = typeof detail === "string" && detail ? detail : "Failed to search Google Books.";
  } finally {
    loading.value = false;
  }
}

function volumeUrl(googleBooksId: string) {
  return `https://books.google.com/books?${new URLSearchParams({ id: googleBooksId })}`;
}
</script>

<template>
  <div class="google-books-id-picker">
    <button type="button" class="btn-small" :disabled="loading || !query" @click="handleSearch">
      {{ loading ? "Searching..." : "Find on Google Books" }}
    </button>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="hasSearched && results.length === 0" class="empty">No matches on Google Books.</p>

    <ul v-if="results.length > 0" class="results" aria-label="Google Books matches">
      <li v-for="result in results" :key="result.google_books_id" class="result">
        <img v-if="result.thumbnail" :src="result.thumbnail" alt="" class="thumbnail" />
        <div class="info">
          <strong>{{ result.title }}</strong>
          <span v-if="result.author">{{ result.author }}</span>
          <span v-if="result.published_date || result.isbn">
            {{ [result.published_date, result.isbn && `ISBN ${result.isbn}`].filter(Boolean).join(" · ") }}
          </span>
          <a :href="volumeUrl(result.google_books_id)" target="_blank" rel="noopener noreferrer">View</a>
        </div>
        <button type="button" class="btn-small" @click="emit('select', result.google_books_id)">Use</button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.google-books-id-picker {
  margin-top: var(--spacing-sm);
}

.empty {
  margin: var(--spacing-sm) 0 0;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.results {
  list-style: none;
  margin: var(--spacing-sm) 0 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.result {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.thumbnail {
  width: 40px;
  border-radius: var(--border-radius);
  flex-shrink: 0;
}

.info {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-width: 0;
  font-size: 14px;
  color: var(--color-text-secondary);
}

.info strong {
  color: var(--color-text);
}
</style>
