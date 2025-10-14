<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import { getBooks, deleteBook } from '../api/books'
import BookCard from '../components/BookCard.vue'
import BookFormModal from '../components/BookFormModal.vue'
import BookSearchModal from '../components/BookSearchModal.vue'
import NavigationBar from '../components/NavigationBar.vue'
import { ReadingStatus, type Book, type PaginatedBooks, type GoogleBookResult } from '../api/types'

const booksData = ref<PaginatedBooks | null>(null)
const loading = ref(false)
const error = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

const showSearchModal = ref(false)
const showFormModal = ref(false)
const editingBook = ref<Book | null>(null)
const prefilledBookData = ref<GoogleBookResult | null>(null)

const filterStatus = ref<ReadingStatus | ''>('')
const searchQuery = ref('')

const filteredBooks = computed(() => {
  if (!booksData.value) return []

  let books = booksData.value.items

  // Filter by status
  if (filterStatus.value) {
    books = books.filter(book => book.user_status?.status === filterStatus.value)
  }

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase().trim()
    books = books.filter(book =>
      book.title.toLowerCase().includes(query) ||
      book.author.toLowerCase().includes(query)
    )
  }

  return books
})

onMounted(() => {
  loadBooks()
})

async function loadBooks() {
  loading.value = true
  error.value = ''

  try {
    booksData.value = await getBooks(currentPage.value, pageSize.value)
  } catch (err: any) {
    console.error('Failed to load books:', err)
    error.value = err.response?.data?.detail || 'Failed to load books. Please try again.'
  } finally {
    loading.value = false
  }
}

function handleAddBook() {
  editingBook.value = null
  prefilledBookData.value = null
  showSearchModal.value = true
}

function handleEditBook(book: Book) {
  editingBook.value = book
  prefilledBookData.value = null
  showFormModal.value = true
}

function handleSearchModalClose() {
  showSearchModal.value = false
}

function handleBookSelected(book: GoogleBookResult) {
  prefilledBookData.value = book
  showSearchModal.value = false
  showFormModal.value = true
}

function handleManualEntry() {
  prefilledBookData.value = null
  showSearchModal.value = false
  showFormModal.value = true
}

async function handleDeleteBook(book: Book) {
  if (!confirm(`Are you sure you want to delete "${book.title}"?`)) {
    return
  }

  try {
    await deleteBook(book.id)
    loadBooks()
  } catch (err: any) {
    console.error('Failed to delete book:', err)
    alert('Failed to delete book. Please try again.')
  }
}

function handleFormModalClose() {
  showFormModal.value = false
  editingBook.value = null
  prefilledBookData.value = null
}

function handleBookSaved() {
  loadBooks()
}

async function goToPage(page: number) {
  currentPage.value = page
  await loadBooks()
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

function getStatusLabel(status: ReadingStatus): string {
  const labels = {
    [ReadingStatus.WANT_TO_READ]: 'Want to read',
    [ReadingStatus.STARTED]: 'Started',
    [ReadingStatus.FINISHED]: 'Finished',
    [ReadingStatus.ABANDONED]: 'Abandoned',
  }
  return labels[status] || status
}
</script>

<template>
  <div>
    <NavigationBar />

    <div class="container">
      <div class="header">
        <h1>My Books</h1>
        <button @click="handleAddBook" class="btn-primary">
          Add Book
        </button>
      </div>

      <div v-if="error" class="error">
        {{ error }}
      </div>

      <div class="filters">
        <div class="filter-group">
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search by title or author..."
            class="search-input"
          />
        </div>

        <div class="filter-group">
          <select v-model="filterStatus" class="filter-select">
            <option value="">All books</option>
            <option :value="ReadingStatus.WANT_TO_READ">
              {{ getStatusLabel(ReadingStatus.WANT_TO_READ) }}
            </option>
            <option :value="ReadingStatus.STARTED">
              {{ getStatusLabel(ReadingStatus.STARTED) }}
            </option>
            <option :value="ReadingStatus.FINISHED">
              {{ getStatusLabel(ReadingStatus.FINISHED) }}
            </option>
            <option :value="ReadingStatus.ABANDONED">
              {{ getStatusLabel(ReadingStatus.ABANDONED) }}
            </option>
          </select>
        </div>
      </div>

      <div v-if="loading" class="loading">
        Loading books...
      </div>

      <div v-else-if="filteredBooks.length === 0" class="empty-state">
        <p v-if="searchQuery || filterStatus">No books match your filters.</p>
        <p v-else>No books yet. Add your first book to get started!</p>
      </div>

      <div v-else class="books-list">
        <BookCard
          v-for="book in filteredBooks"
          :key="book.id"
          :book="book"
          @updated="handleEditBook(book)"
          @deleted="handleDeleteBook(book)"
        />
      </div>

      <div v-if="booksData && booksData.pages > 1" class="pagination">
        <button
          @click="goToPage(currentPage - 1)"
          :disabled="currentPage === 1"
        >
          Previous
        </button>
        <span class="pagination-info">
          Page {{ currentPage }} of {{ booksData.pages }}
        </span>
        <button
          @click="goToPage(currentPage + 1)"
          :disabled="currentPage === booksData.pages"
        >
          Next
        </button>
      </div>
    </div>

    <BookSearchModal
      v-if="showSearchModal"
      @close="handleSearchModalClose"
      @select="handleBookSelected"
      @manualEntry="handleManualEntry"
    />

    <BookFormModal
      v-if="showFormModal"
      :book="editingBook"
      :prefilled-data="prefilledBookData"
      @close="handleFormModalClose"
      @saved="handleBookSaved"
    />
  </div>
</template>

<style scoped>
.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--spacing-lg);
}

.header h1 {
  margin: 0;
}

.filters {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-lg);
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
}

.filter-group {
  flex: 1;
}

.search-input {
  width: 100%;
}

.filter-select {
  width: 100%;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

.books-list {
  margin-top: var(--spacing-lg);
}

.pagination-info {
  color: var(--color-text-secondary);
  font-size: 14px;
}

@media (max-width: 768px) {
  .header {
    flex-direction: column;
    align-items: stretch;
    gap: var(--spacing-md);
  }

  .filters {
    flex-direction: column;
  }
}
</style>
