<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getBook, setReadingStatus, removeReadingStatus, deleteBook } from '../api/books'
import BookFormModal from '../components/BookFormModal.vue'
import BookSearchModal from '../components/BookSearchModal.vue'
import NavigationBar from '../components/NavigationBar.vue'
import { ReadingStatus, type Book, type GoogleBookResult } from '../api/types'

const router = useRouter()
const route = useRoute()

const book = ref<Book | null>(null)
const loading = ref(false)
const error = ref('')
const updatingStatus = ref(false)
const showEditModal = ref(false)
const showSearchModal = ref(false)
const showFormModal = ref(false)
const prefilledBookData = ref<GoogleBookResult | null>(null)

const statusOptions = [
  { value: '', label: 'No status' },
  { value: ReadingStatus.WANT_TO_READ, label: 'Want to read' },
  { value: ReadingStatus.STARTED, label: 'Started' },
  { value: ReadingStatus.FINISHED, label: 'Finished' },
  { value: ReadingStatus.ABANDONED, label: 'Abandoned' },
]

onMounted(() => {
  loadBook()
})

async function loadBook() {
  const bookId = parseInt(route.params.id as string)
  if (isNaN(bookId)) {
    error.value = 'Invalid book ID'
    return
  }

  loading.value = true
  error.value = ''

  try {
    book.value = await getBook(bookId)
  } catch (err: any) {
    console.error('Failed to load book:', err)
    error.value = err.response?.data?.detail || 'Failed to load book. Please try again.'
  } finally {
    loading.value = false
  }
}

async function handleStatusChange(event: Event) {
  if (!book.value) return

  const newStatus = (event.target as HTMLSelectElement).value
  updatingStatus.value = true

  try {
    if (newStatus === '') {
      await removeReadingStatus(book.value.id)
    } else {
      await setReadingStatus(book.value.id, {
        status: newStatus as ReadingStatus,
      })
    }
    await loadBook()
  } catch (error) {
    console.error('Failed to update reading status:', error)
    alert('Failed to update reading status')
  } finally {
    updatingStatus.value = false
  }
}

function getStatusColor(status: ReadingStatus | null): string {
  if (!status) return 'var(--color-text-secondary)'

  switch (status) {
    case ReadingStatus.WANT_TO_READ:
      return 'var(--color-primary)'
    case ReadingStatus.STARTED:
      return 'var(--color-warning)'
    case ReadingStatus.FINISHED:
      return 'var(--color-success)'
    case ReadingStatus.ABANDONED:
      return 'var(--color-text-secondary)'
    default:
      return 'var(--color-text-secondary)'
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString()
}

function handleEdit() {
  showEditModal.value = true
}

async function handleDelete() {
  if (!book.value) return

  if (!confirm(`Are you sure you want to delete "${book.value.title}"?`)) {
    return
  }

  try {
    await deleteBook(book.value.id)
    router.push({ name: 'books' })
  } catch (err: any) {
    console.error('Failed to delete book:', err)
    alert('Failed to delete book. Please try again.')
  }
}

function handleModalClose() {
  showEditModal.value = false
}

function handleBookSaved() {
  loadBook()
}

function goBack() {
  router.push({ name: 'books' })
}

function handleAddBook() {
  showSearchModal.value = true
}

function handleSearchModalClose() {
  showSearchModal.value = false
}

function handleBookSelected(selectedBook: GoogleBookResult) {
  prefilledBookData.value = selectedBook
  showSearchModal.value = false
  showFormModal.value = true
}

function handleManualEntry() {
  prefilledBookData.value = null
  showSearchModal.value = false
  showFormModal.value = true
}

function handleFormModalClose() {
  showFormModal.value = false
  prefilledBookData.value = null
}

function handleNewBookSaved() {
  showFormModal.value = false
  prefilledBookData.value = null
  router.push({ name: 'books' })
}
</script>

<template>
  <div>
    <NavigationBar @add-book="handleAddBook" />

    <div class="container">
      <div class="back-button">
        <button @click="goBack">
          &larr; Back to Books
        </button>
      </div>

      <div v-if="loading" class="loading">
        Loading book...
      </div>

      <div v-else-if="error" class="error">
        {{ error }}
      </div>

      <div v-else-if="book" class="book-detail">
        <div class="book-header">
          <div class="book-cover-section">
            <img
              v-if="book.cover_image_url"
              :src="book.cover_image_url"
              :alt="book.title"
              class="book-cover-large"
            />
            <div v-else class="book-cover-large book-cover-placeholder">
              No Cover
            </div>
          </div>

          <div class="book-info">
            <h1>{{ book.title }}</h1>
            <p class="book-author">by {{ book.author }}</p>

            <div class="book-actions">
              <button @click="handleEdit" class="btn-primary">
                Edit Book
              </button>
              <button @click="handleDelete" class="btn-danger">
                Delete Book
              </button>
            </div>

            <div class="book-status-section">
              <label for="status">Reading status:</label>
              <select
                id="status"
                :value="book.user_status?.status || ''"
                @change="handleStatusChange"
                :disabled="updatingStatus"
                :style="{ borderColor: getStatusColor(book.user_status?.status || null) }"
              >
                <option v-for="option in statusOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </div>

            <div v-if="book.user_status" class="book-dates">
              <div v-if="book.user_status.started_at" class="date-item">
                <strong>Started:</strong> {{ formatDate(book.user_status.started_at) }}
              </div>
              <div v-if="book.user_status.finished_at" class="date-item">
                <strong>Finished:</strong> {{ formatDate(book.user_status.finished_at) }}
              </div>
            </div>
          </div>
        </div>

        <div class="book-body">
          <div v-if="book.description" class="book-description">
            <h2>Description</h2>
            <p>{{ book.description }}</p>
          </div>

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
                <strong>Published:</strong> {{ formatDate(book.published_date) }}
              </div>
              <div class="metadata-item">
                <strong>Added:</strong> {{ formatDate(book.created_at) }}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <BookFormModal
      v-if="showEditModal && book"
      :book="book"
      @close="handleModalClose"
      @saved="handleBookSaved"
    />

    <BookSearchModal
      v-if="showSearchModal"
      @close="handleSearchModalClose"
      @select="handleBookSelected"
      @manualEntry="handleManualEntry"
    />

    <BookFormModal
      v-if="showFormModal"
      :prefilled-data="prefilledBookData"
      @close="handleFormModalClose"
      @saved="handleNewBookSaved"
    />
  </div>
</template>

<style scoped>
.back-button {
  margin-bottom: var(--spacing-lg);
}

.book-detail {
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  overflow: hidden;
}

.book-header {
  display: flex;
  gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  background-color: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
}

.book-cover-section {
  flex-shrink: 0;
}

.book-cover-large {
  width: 240px;
  height: 360px;
  object-fit: cover;
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
}

.book-cover-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 14px;
  text-align: center;
}

.book-info {
  flex: 1;
  min-width: 0;
}

.book-info h1 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 2rem;
  line-height: 1.2;
}

.book-author {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-secondary);
  font-size: 1.125rem;
}

.book-actions {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
}

.book-status-section {
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
}

.book-status-section label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-weight: 500;
  font-size: 14px;
}

.book-status-section select {
  width: 100%;
  max-width: 300px;
  border-width: 2px;
  transition: border-color 0.15s ease;
}

.book-dates {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.date-item {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.date-item strong {
  color: var(--color-text);
}

.book-body {
  padding: var(--spacing-xl);
}

.book-description {
  margin-bottom: var(--spacing-xl);
}

.book-description h2 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

.book-description p {
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
}

.book-metadata h2 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

.metadata-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: var(--spacing-md);
}

.metadata-item {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.metadata-item strong {
  color: var(--color-text);
}

@media (max-width: 768px) {
  .book-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
  }

  .book-cover-large {
    width: 200px;
    height: 300px;
  }

  .book-info h1 {
    font-size: 1.5rem;
  }

  .book-actions {
    flex-direction: column;
  }

  .book-actions button {
    width: 100%;
  }

  .book-status-section select {
    max-width: 100%;
  }

  .metadata-grid {
    grid-template-columns: 1fr;
  }
}
</style>
