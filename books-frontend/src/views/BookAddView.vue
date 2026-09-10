<script setup lang="ts">
import { isAxiosError } from "axios";
import { onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import NavigationBar from "../components/navigation/NavigationBar.vue";
import { createBook, searchGoogleBooks } from "../api/books";
import { invalidateCache } from "../cache/invalidate";
import type { GoogleBookResult } from "../api/types";

const router = useRouter();
const addingBook = ref(false);
let isUnmounted = false;

onBeforeUnmount(() => {
  isUnmounted = true;
});

const searchQuery = ref("");
const searchResults = ref<GoogleBookResult[]>([]);
const loading = ref(false);
const error = ref("");
const hasSearched = ref(false);

async function handleSearch() {
  if (loading.value || addingBook.value) {
    return;
  }

  if (!searchQuery.value.trim()) {
    error.value = "Please enter a search query";
    return;
  }

  error.value = "";
  loading.value = true;
  hasSearched.value = true;

  try {
    searchResults.value = await searchGoogleBooks(searchQuery.value);
  } catch (err) {
    console.error("Failed to search books:", err);
    const detail = isAxiosError<{ detail?: unknown }>(err) ? err.response?.data?.detail : undefined;
    error.value = typeof detail === "string" && detail ? detail : "Failed to search books. Please try again.";
  } finally {
    loading.value = false;
  }
}

async function handleSelectBook(book: GoogleBookResult) {
  if (addingBook.value) {
    return;
  }

  addingBook.value = true;
  error.value = "";

  try {
    await createBook({
      title: book.title,
      author: book.author,
      isbn: book.isbn || undefined,
      description: book.description || undefined,
      published_date: book.published_date || undefined,
      page_count: book.page_count ?? undefined,
      cover_image_url: book.thumbnail || undefined,
    });

    await invalidateCache.bookAdded();

    if (!isUnmounted) {
      await router.push({ name: "books" });
    }
  } catch (err) {
    console.error("Failed to add book:", err);
    const detail = isAxiosError<{ detail?: unknown }>(err) ? err.response?.data?.detail : undefined;
    error.value = typeof detail === "string" && detail ? detail : "Failed to add book. Please try again.";
  } finally {
    addingBook.value = false;
  }
}
</script>

<template>
  <div class="book-add-view">
    <NavigationBar />
    <main class="container-narrow">
      <div class="page-header">
        <h1>Add book</h1>

        <RouterLink :to="{ name: 'books' }" class="btn btn-small">Cancel</RouterLink>
      </div>

      <div>
        <div class="search-section">
          <p class="search-description">Search Google Books to quickly add book details</p>

          <form class="search-input-group" @submit.prevent="handleSearch">
            <input
              v-model="searchQuery"
              type="text"
              aria-label="Book title, author, or ISBN"
              placeholder="Enter book title, author, or ISBN..."
              class="search-input"
              :disabled="loading || addingBook"
            />
            <button type="submit" class="btn-primary" :disabled="loading || addingBook || !searchQuery.trim()">
              {{ loading ? "Searching..." : "Search" }}
            </button>
          </form>
        </div>

        <div v-if="error" class="error" role="alert">
          {{ error }}
        </div>

        <div v-if="loading" class="loading">Searching books...</div>

        <div v-else-if="hasSearched && searchResults.length === 0" class="empty-state">
          <p>No books found. Try a different search term.</p>
        </div>

        <div v-else-if="searchResults.length > 0" class="results-section">
          <h4>Search Results</h4>
          <div class="results-list">
            <div v-for="(book, index) in searchResults" :key="book.google_books_id || index" class="result-item">
              <div class="result-content">
                <img v-if="book.thumbnail" :src="book.thumbnail" :alt="book.title" class="book-thumbnail" />
                <div v-else class="book-thumbnail-placeholder">No Image</div>
                <div class="book-info">
                  <h5 class="book-title">{{ book.title }}</h5>
                  <p class="book-author">{{ book.author }}</p>
                  <div class="book-details">
                    <span v-if="book.published_date" class="detail">
                      {{ book.published_date }}
                    </span>
                    <span v-if="book.page_count" class="detail"> {{ book.page_count }} pages </span>
                    <span v-if="book.isbn" class="detail"> ISBN: {{ book.isbn }} </span>
                  </div>
                  <p v-if="book.description" class="book-description">
                    {{ book.description.substring(0, 150) }}{{ book.description.length > 150 ? "..." : "" }}
                  </p>
                </div>
              </div>
              <button class="btn-select" :disabled="addingBook" @click="handleSelectBook(book)">
                {{ addingBook ? "Adding..." : "Add book" }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </main>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.search-section {
  margin-bottom: var(--spacing-lg);
}

.search-description {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-md);
  font-size: 14px;
}

.search-input-group {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.search-input {
  flex: 1;
}

.results-section {
  margin-top: var(--spacing-lg);
  padding-top: var(--spacing-lg);
  border-top: 1px solid var(--color-border);
}

.results-section h4 {
  margin: 0 0 var(--spacing-md) 0;
  color: var(--color-text);
}

.results-list {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: var(--spacing-md);
  padding: var(--spacing-md);
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
}

.result-content {
  display: flex;
  gap: var(--spacing-md);
  flex: 1;
  min-width: 0;
}

.book-thumbnail,
.book-thumbnail-placeholder {
  width: 80px;
  height: auto;
  border-radius: var(--border-radius);
  flex-shrink: 0;
}

.book-thumbnail {
  display: block;
}

.book-thumbnail-placeholder {
  aspect-ratio: 2 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 12px;
  text-align: center;
}

.book-info {
  flex: 1;
  min-width: 0;
}

.book-title {
  margin: 0 0 4px 0;
  font-size: 16px;
  color: var(--color-text);
}

.book-author {
  margin: 0 0 8px 0;
  color: var(--color-text-secondary);
  font-size: 14px;
}

.book-details {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  margin-bottom: 8px;
}

.detail {
  font-size: 12px;
  color: var(--color-text-secondary);
  padding: 2px 8px;
  background-color: var(--color-bg);
  border-radius: 4px;
}

.book-description {
  margin: 0;
  font-size: 13px;
  color: var(--color-text-secondary);
  line-height: 1.4;
}

.btn-select {
  flex-shrink: 0;
  padding: var(--spacing-sm) var(--spacing-md);
  background-color: var(--color-primary);
  color: white;
  border: none;
  border-radius: var(--border-radius);
  cursor: pointer;
  font-size: 14px;
  height: fit-content;
}

.btn-select:hover {
  opacity: 0.9;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .search-input-group {
    flex-direction: column;
  }

  .search-input-group button {
    width: 100%;
  }

  .result-content {
    flex-direction: column;
  }

  .result-item {
    flex-direction: column;
    width: 100%;
  }

  .results-list {
    overflow-x: hidden;
  }

  .btn-select {
    width: 100%;
  }
}
</style>
