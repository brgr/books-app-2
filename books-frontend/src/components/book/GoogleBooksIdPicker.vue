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
</script>

<template>
  <div>
    <button type="button" class="btn-small" :disabled="loading || !query" @click="handleSearch">
      {{ loading ? "Searching..." : "Find on Google Books" }}
    </button>

    <p v-if="error" class="error" role="alert">{{ error }}</p>
    <p v-else-if="hasSearched && results.length === 0">No matches on Google Books.</p>

    <ul v-if="results.length > 0" aria-label="Google Books matches">
      <li v-for="result in results" :key="result.google_books_id">
        <div>
          <strong>{{ result.title }}</strong>
          <span v-if="result.author">{{ result.author }}</span>
        </div>
        <button type="button" class="btn-small" @click="emit('select', result.google_books_id)">Use</button>
      </li>
    </ul>
  </div>
</template>
