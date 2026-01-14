<script setup lang="ts">
import {computed, ref, onMounted} from 'vue'
import {useRouter, useRoute} from 'vue-router'
import {getBook, setReadingStatus, deleteBook, getBookEvents} from '../api/books'
import {getMediaUrl} from '../api/client'
import BookFormModal from '../components/BookFormModal.vue'
import BookSearchModal from '../components/BookSearchModal.vue'
import NavigationBar from '../components/NavigationBar.vue'
import EventTimeline from '../components/EventTimeline.vue'
import {ReadingStatus, type Book, type GoogleBookResult, type BookEvent} from '../api/types'
import {formatShortDate} from '../utils/date'

const router = useRouter()
const route = useRoute()

const book = ref<Book | null>(null)
const events = ref<BookEvent[]>([])
const loading = ref(false)
const error = ref('')
const updatingStatus = ref(false)
const showEditModal = ref(false)
const showSearchModal = ref(false)
const showFormModal = ref(false)
const prefilledBookData = ref<GoogleBookResult | null>(null)

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
    await loadEvents(bookId)
  } catch (err: any) {
    console.error('Failed to load book:', err)
    error.value = err.response?.data?.detail || 'Failed to load book. Please try again.'
  } finally {
    loading.value = false
  }
}

async function loadEvents(bookId: number) {
  try {
    events.value = await getBookEvents(bookId)
  } catch (err) {
    console.error('Failed to load events:', err)
    // Don't show error to user for events, they're not critical
  }
}

const canStartReading = computed(() => {
  const status = book.value?.user_status?.status || null
  return status === null || status === ReadingStatus.WANT_TO_READ
})

const canFinishReading = computed(() => book.value?.user_status?.status === ReadingStatus.STARTED)

async function handleStartReading() {
  if (!book.value) return
  updatingStatus.value = true

  try {
    await setReadingStatus(book.value.id, {status: ReadingStatus.STARTED})
    await loadBook()
  } catch (error) {
    console.error('Failed to start reading:', error)
    alert('Failed to start reading')
  } finally {
    updatingStatus.value = false
  }
}

async function handleFinishReading() {
  if (!book.value) return
  updatingStatus.value = true

  try {
    await setReadingStatus(book.value.id, {status: ReadingStatus.FINISHED})
    await loadBook()
  } catch (error) {
    console.error('Failed to finish reading:', error)
    alert('Failed to finish reading')
  } finally {
    updatingStatus.value = false
  }
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
    router.push({name: 'books'})
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
  router.push({name: 'books'})
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
  router.push({name: 'books'})
}
</script>

<template>
  <div>
    <NavigationBar @add-book="handleAddBook"/>

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
                :src="getMediaUrl(book.cover_image_url)"
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
              <div class="status-actions">
                <button
                    v-if="canStartReading"
                    class="btn-secondary"
                    @click="handleStartReading"
                    :disabled="updatingStatus"
                >
                  Start Reading
                </button>
                <button
                    v-if="canFinishReading"
                    class="btn-primary"
                    @click="handleFinishReading"
                    :disabled="updatingStatus"
                >
                  Finish Reading
                </button>
              </div>
            </div>

            <div v-if="book.user_status" class="book-dates">
              <div v-if="book.user_status.started_at" class="date-item">
                <strong>Started:</strong> {{ formatShortDate(book.user_status.started_at) }}
              </div>
              <div v-if="book.user_status.finished_at" class="date-item">
                <strong>Finished:</strong> {{ formatShortDate(book.user_status.finished_at) }}
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
                <strong>Published:</strong> {{ formatShortDate(book.published_date) }}
              </div>
              <div class="metadata-item">
                <strong>Added:</strong> {{ formatShortDate(book.created_at) }}
              </div>
            </div>
          </div>

          <EventTimeline :events="events" />
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
  max-width: 100%;
}

.book-header {
  display: flex;
  gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  background-color: var(--color-bg);
  border-bottom: 1px solid var(--color-border);
  flex-wrap: wrap;
  max-width: 100%;
}

.book-cover-section {
  flex-shrink: 0;
  max-width: 100%;
}

.book-cover-large {
  width: min(240px, 100%);
  max-width: 100%;
  aspect-ratio: 2 / 3;
  height: auto;
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
  width: 100%;
}

.book-info h1 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 2rem;
  line-height: 1.2;
  word-break: break-word;
}

.book-author {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-secondary);
  font-size: 1.125rem;
  word-break: break-word;
}

.book-actions {
  display: flex;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
}

.book-actions button {
  flex: 1 1 180px;
  min-width: 0;
}

.book-status-section {
  margin-bottom: var(--spacing-lg);
  padding: 0;
  background-color: transparent;
  border: none;
}

.status-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
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
  overflow-x: hidden;
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
  word-break: break-word;
  overflow-wrap: anywhere;
}

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
  .book-detail {
    border: none;
    border-radius: 0;
    box-shadow: none;
    background-color: transparent;
  }

  .book-header {
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--spacing-lg);
  }

  .book-cover-large {
    width: min(200px, 100%);
    height: auto;
    aspect-ratio: 2 / 3;
  }

  .book-info h1 {
    font-size: 1.5rem;
  }

  .book-actions {
    flex-direction: column;
  }

  .book-actions button {
    width: 100%;
    flex: 0 0 auto;
  }

  .book-status-section select {
    max-width: 100%;
  }

  .book-body {
    padding: var(--spacing-lg);
  }

  .metadata-grid {
    grid-template-columns: 1fr;
  }
}
</style>
