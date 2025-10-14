<script setup lang="ts">
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { getBooks, deleteBook } from '../api/books'
import BookCard from '../components/BookCard.vue'
import BookFormModal from '../components/BookFormModal.vue'
import BookSearchModal from '../components/BookSearchModal.vue'
import NavigationBar from '../components/NavigationBar.vue'
import { ReadingStatus, type Book, type PaginatedBooks, type GoogleBookResult } from '../api/types'

const router = useRouter()

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

// Load saved view mode from localStorage, default to 'list'
const savedViewMode = localStorage.getItem('booksViewMode') as 'list' | 'grid' | null
const viewMode = ref<'list' | 'grid'>(savedViewMode || 'list')

// Watch viewMode and save to localStorage whenever it changes
watch(viewMode, (newMode) => {
  localStorage.setItem('booksViewMode', newMode)
})

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

function handleViewBook(book: Book) {
  router.push({ name: 'book-detail', params: { id: book.id } })
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

        <div class="view-toggle">
          <button
            @click="viewMode = 'list'"
            :class="['view-toggle-btn', { active: viewMode === 'list' }]"
            title="List view"
          >
            List
          </button>
          <button
            @click="viewMode = 'grid'"
            :class="['view-toggle-btn', { active: viewMode === 'grid' }]"
            title="Grid view"
          >
            Grid
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading">
        Loading books...
      </div>

      <div v-else-if="filteredBooks.length === 0" class="empty-state">
        <p v-if="searchQuery || filterStatus">No books match your filters.</p>
        <p v-else>No books yet. Add your first book to get started!</p>
      </div>

      <div v-else :class="['books-container', viewMode === 'grid' ? 'books-grid' : 'books-list']">
        <div
          v-for="book in filteredBooks"
          :key="book.id"
          :class="viewMode === 'grid' ? 'grid-item' : ''"
        >
          <img
            v-if="viewMode === 'grid' && book.cover_image_url"
            :src="book.cover_image_url"
            :alt="book.title"
            :title="book.title + ' by ' + book.author"
            class="grid-cover"
            @click="handleViewBook(book)"
          />
          <div
            v-else-if="viewMode === 'grid'"
            class="grid-cover-placeholder"
            :title="book.title + ' by ' + book.author"
            @click="handleViewBook(book)"
          >
            <div class="grid-no-cover-text">{{ book.title }}</div>
          </div>
          <BookCard
            v-else
            :book="book"
            @click="handleViewBook(book)"
            @updated="handleEditBook(book)"
            @deleted="handleDeleteBook(book)"
          />
        </div>
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
  align-items: center;
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

.view-toggle {
  display: flex;
  gap: 4px;
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  padding: 4px;
}

.view-toggle-btn {
  padding: 6px 16px;
  background: transparent;
  border: none;
  border-radius: calc(var(--border-radius) - 2px);
  cursor: pointer;
  color: var(--color-text-secondary);
  font-size: 14px;
  transition: all 0.2s ease;
}

.view-toggle-btn:hover {
  color: var(--color-text);
  background-color: var(--color-bg-card);
}

.view-toggle-btn.active {
  background-color: var(--color-primary);
  color: white;
}

.view-toggle-btn.active:hover {
  background-color: var(--color-primary);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

.books-container {
  margin-top: var(--spacing-lg);
}

.books-list {
  display: flex;
  flex-direction: column;
}

.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--spacing-lg);
}

.grid-item {
  display: flex;
  flex-direction: column;
}

.grid-cover {
  width: 100%;
  aspect-ratio: 2/3;
  object-fit: cover;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: var(--shadow);
}

.grid-cover:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.grid-cover-placeholder {
  width: 100%;
  aspect-ratio: 2/3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  box-shadow: var(--shadow);
  padding: var(--spacing-md);
}

.grid-cover-placeholder:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.grid-no-cover-text {
  text-align: center;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 500;
  word-break: break-word;
  line-height: 1.4;
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

  .view-toggle {
    width: 100%;
  }

  .view-toggle-btn {
    flex: 1;
  }

  .books-grid {
    grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
    gap: var(--spacing-md);
  }
}
</style>
