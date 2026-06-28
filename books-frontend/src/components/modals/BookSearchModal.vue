<script setup lang="ts">
import { ref } from 'vue'
import { searchGoogleBooks } from '../../api/books'
import type { GoogleBookResult } from '../../api/types'

const emit = defineEmits<{
  close: []
  select: [book: GoogleBookResult]
}>()

const searchQuery = ref('')
const searchResults = ref<GoogleBookResult[]>([])
const loading = ref(false)
const error = ref('')
const hasSearched = ref(false)

async function handleSearch() {
  if (!searchQuery.value.trim()) {
    error.value = 'Please enter a search query'
    return
  }

  error.value = ''
  loading.value = true
  hasSearched.value = true

  try {
    searchResults.value = await searchGoogleBooks(searchQuery.value)
  } catch (err: any) {
    console.error('Failed to search books:', err)
    error.value = err.response?.data?.detail || 'Failed to search books. Please try again.'
  } finally {
    loading.value = false
  }
}

function handleSelectBook(book: GoogleBookResult) {
  emit('select', book)
}

function handleClose() {
  if (!loading.value) {
    emit('close')
  }
}

function handleKeyPress(event: KeyboardEvent) {
  if (event.key === 'Enter') {
    handleSearch()
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal">
      <div class="modal-header">
        <h3>Search for a Book</h3>
        <button @click="handleClose" :disabled="loading" class="btn-small">
          Close
        </button>
      </div>

      <div class="modal-body">
        <div class="search-section">
          <p class="search-description">
            Search Google Books to quickly add book details
          </p>

          <div class="search-input-group">
            <input
              v-model="searchQuery"
              type="text"
              placeholder="Enter book title, author, or ISBN..."
              class="search-input"
              :disabled="loading"
              @keypress="handleKeyPress"
            />
            <button @click="handleSearch" class="btn-primary" :disabled="loading || !searchQuery.trim()">
              {{ loading ? 'Searching...' : 'Search' }}
            </button>
          </div>

        </div>

        <div v-if="error" class="error">
          {{ error }}
        </div>

        <div v-if="loading" class="loading">
          Searching books...
        </div>

        <div v-else-if="hasSearched && searchResults.length === 0" class="empty-state">
          <p>No books found. Try a different search term.</p>
        </div>

        <div v-else-if="searchResults.length > 0" class="results-section">
          <h4>Search Results</h4>
          <div class="results-list">
            <div
              v-for="(book, index) in searchResults"
              :key="book.google_books_id || index"
              class="result-item"
            >
              <div class="result-content">
                <img
                  v-if="book.thumbnail"
                  :src="book.thumbnail"
                  :alt="book.title"
                  class="book-thumbnail"
                />
                <div class="book-thumbnail-placeholder" v-else>
                  No Image
                </div>
                <div class="book-info">
                  <h5 class="book-title">{{ book.title }}</h5>
                  <p class="book-author">{{ book.author }}</p>
                  <div class="book-details">
                    <span v-if="book.published_date" class="detail">
                      {{ book.published_date }}
                    </span>
                    <span v-if="book.page_count" class="detail">
                      {{ book.page_count }} pages
                    </span>
                    <span v-if="book.isbn" class="detail">
                      ISBN: {{ book.isbn }}
                    </span>
                  </div>
                  <p v-if="book.description" class="book-description">
                    {{ book.description.substring(0, 150) }}{{ book.description.length > 150 ? '...' : '' }}
                  </p>
                </div>
              </div>
              <button @click="handleSelectBook(book)" class="btn-select">
                Select
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
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
  max-height: 400px;
  overflow-y: auto;
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
