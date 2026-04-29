<script setup lang="ts">
import {computed, ref} from 'vue'
import {useRouter, useRoute} from 'vue-router'
import {createBook, getBook, setReadingStatus, getBookEvents, addBookProgress} from '../api/books'
import {getMediaUrl} from '../api/client'
import BookNotes from '../components/BookNotes.vue'
import BookSearchModal from '../components/BookSearchModal.vue'
import BookStatusSheet from '../components/BookStatusSheet.vue'
import NavigationBar from '../components/NavigationBar.vue'
import EventTimeline from '../components/EventTimeline.vue'
import {ReadingStatus, type Book, type GoogleBookResult, type BookEvent} from '../api/types'
import {formatShortDate} from '../utils/date'
import {useCachedQuery} from '../composables/useCachedQuery'
import {useClampToggle} from '../composables/useClampToggle'
import {cacheKeys} from '../cache/keys'
import {cacheDel, cacheInvalidateByPrefix} from '../cache/store'

const router = useRouter()
const route = useRoute()

const bookId = computed(() => {
  const id = parseInt(route.params.id as string)
  return isNaN(id) ? 0 : id
})

const {
  data: book,
  error: bookError,
  refresh: refreshBook,
} = useCachedQuery<Book>(
  computed(() => bookId.value ? cacheKeys.book(bookId.value) : ''),
  () => getBook(bookId.value),
  { enabled: computed(() => bookId.value > 0) }
)

const {
  data: events,
  refresh: refreshEvents,
} = useCachedQuery<BookEvent[]>(
  computed(() => bookId.value ? cacheKeys.bookEvents(bookId.value) : ''),
  () => getBookEvents(bookId.value),
  { enabled: computed(() => bookId.value > 0) }
)

const error = computed(() => {
  const e = bookError.value
  if (!e) return ''
  if (e instanceof Error) return e.message
  return 'Failed to load book. Please try again.'
})
const updatingStatus = ref(false)
const notesSaving = ref(false)
const progressSaving = ref(false)
const showSearchModal = ref(false)
const addingBook = ref(false)
const descriptionRef = ref<HTMLElement | null>(null)
const {
  expanded: descriptionExpanded,
  showToggle: showDescriptionToggle,
  maxHeight: descriptionMaxHeight,
  toggle: toggleDescription,
} = useClampToggle(descriptionRef, {source: computed(() => book.value?.description)})

async function loadBook() {
  await cacheDel(cacheKeys.book(bookId.value))
  await cacheDel(cacheKeys.bookEvents(bookId.value))
  await refreshBook()
  await refreshEvents()
}

const canUpdateProgress = computed(() => book.value?.user_status?.status === ReadingStatus.STARTED)


const progressSummary = computed(() => {
  if (!book.value) return ''
  const currentPage = book.value.user_status?.current_page
  if (currentPage === null || currentPage === undefined) {
    return 'No progress yet'
  }
  if (book.value.page_count) {
    return `Page ${currentPage} of ${book.value.page_count}`
  }
  return `Page ${currentPage}`
})

const readingStatusLabel = computed(() => {
  const status = book.value?.user_status?.status ?? ReadingStatus.WANT_TO_READ
  if (status === ReadingStatus.STARTED) return 'Reading'
  if (status === ReadingStatus.FINISHED) return 'Finished'
  return 'Want to read'
})

const readingStatusSubtitle = computed(() => {
  if (!book.value) return ''
  if (readingStatusLabel.value === 'Reading') return progressSummary.value
  if (readingStatusLabel.value === 'Finished') {
    if (book.value.user_status?.finished_at) {
      return `Finished ${formatShortDate(book.value.user_status.finished_at)}`
    }
    return 'Finished'
  }
  return 'Not started yet'
})

async function changeStatus(status: ReadingStatus, occurredAt?: string) {
  if (!book.value) return
  updatingStatus.value = true
  try {
    await setReadingStatus(book.value.id, {status, occurred_at: occurredAt})
    await cacheInvalidateByPrefix('lists:')
    await loadBook()
  } catch (err) {
    console.error('Failed to update reading status:', err)
    alert('Failed to update reading status')
  } finally {
    updatingStatus.value = false
  }
}

function handleStartReading(payload: {occurredAt?: string}) {
  return changeStatus(ReadingStatus.STARTED, payload.occurredAt)
}

function handleFinishReading(payload: {occurredAt?: string}) {
  return changeStatus(ReadingStatus.FINISHED, payload.occurredAt)
}

async function handleSaveNotes(notes: string) {
  if (!book.value) return
  notesSaving.value = true
  try {
    const status = book.value.user_status?.status ?? ReadingStatus.WANT_TO_READ
    book.value.user_status = await setReadingStatus(book.value.id, {status, notes})
    await cacheDel(cacheKeys.bookEvents(book.value.id))
    await refreshEvents()
  } catch (error) {
    console.error('Failed to save notes:', error)
    alert('Failed to save notes')
  } finally {
    notesSaving.value = false
  }
}

async function handleSaveProgress(page: number) {
  if (!book.value || !canUpdateProgress.value) return
  progressSaving.value = true
  try {
    book.value.user_status = await addBookProgress(book.value.id, {page})
    await cacheDel(cacheKeys.bookEvents(book.value.id))
    await refreshEvents()
  } catch (error) {
    console.error('Failed to save progress:', error)
    alert('Failed to save progress')
  } finally {
    progressSaving.value = false
  }
}

function handleEdit() {
  if (!book.value) return
  router.push({name: 'book-edit', params: {id: book.value.id}})
}

function handleAddBook() {
  showSearchModal.value = true
}

function handleSearchModalClose() {
  if (addingBook.value) return
  showSearchModal.value = false
}

async function handleBookSelected(selectedBook: GoogleBookResult) {
  if (addingBook.value) return
  addingBook.value = true
  try {
    await createBook({
      title: selectedBook.title,
      author: selectedBook.author,
      isbn: selectedBook.isbn || undefined,
      description: selectedBook.description || undefined,
      published_date: selectedBook.published_date || undefined,
      page_count: selectedBook.page_count ?? undefined,
      cover_image_url: selectedBook.thumbnail || undefined,
    })
    await cacheInvalidateByPrefix('lists:')
    showSearchModal.value = false
    router.push({name: 'books'})
  } catch (err: any) {
    console.error('Failed to add book:', err)
    alert(err.response?.data?.detail || 'Failed to add book. Please try again.')
  } finally {
    addingBook.value = false
  }
}

</script>

<template>
  <div class="book-detail-page">
    <NavigationBar @add-book="handleAddBook"/>

    <div class="container">
      <div v-if="!book && !error" class="loading">
        Loading book...
      </div>

      <div v-else-if="error && !book" class="error">
        {{ error }}
      </div>

      <div v-else-if="book" class="book-detail">
        <div class="book-header">
          <div class="book-cover-section">
              <img
                v-if="book.cover_image_url || book.cover_thumbnail_url"
                :src="getMediaUrl(book.cover_image_url || book.cover_thumbnail_url)"
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

            <div class="book-status-section">
              <BookStatusSheet
                :status="book.user_status?.status ?? null"
                :status-label="readingStatusLabel"
                :status-subtitle="readingStatusSubtitle"
                :updating="updatingStatus"
                :current-page="book.user_status?.current_page ?? null"
                :page-count="book.page_count ?? null"
                :progress-saving="progressSaving"
                @start="handleStartReading"
                @finish="handleFinishReading"
                @update-progress="handleSaveProgress"
              />
            </div>

            <div v-if="book.user_status" class="book-dates">
              <div v-if="book.user_status.started_at" class="date-item">
                <strong>Started:</strong> {{ formatShortDate(book.user_status.started_at) }}
              </div>
              <div v-if="book.user_status.finished_at" class="date-item">
                <strong>Finished:</strong> {{ formatShortDate(book.user_status.finished_at) }}
              </div>
              <div v-if="book.user_status.current_page !== null" class="date-item">
                <strong>Current page:</strong>
                {{ book.user_status.current_page }}
                <span v-if="book.page_count">/ {{ book.page_count }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="book-body">
          <div v-if="book.description" class="book-description">
            <h2>Description</h2>
            <p
              ref="descriptionRef"
              class="description-text"
              :class="{
                clamped: showDescriptionToggle && !descriptionExpanded,
              }"
              :style="{maxHeight: descriptionMaxHeight}"
            >
              {{ book.description }}
            </p>
            <button
              v-if="showDescriptionToggle"
              type="button"
              class="description-toggle"
              @click="toggleDescription"
            >
              {{ descriptionExpanded ? 'Read less' : 'Read more...' }}
            </button>
          </div>

          <BookNotes
            :notes="book.user_status?.notes ?? ''"
            :saving="notesSaving"
            @save="handleSaveNotes"
          />

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
              <div v-if="book.user_status && book.user_status.current_page !== null" class="metadata-item">
                <strong>Current page:</strong>
                {{ book.user_status.current_page }}
                <span v-if="book.page_count">/ {{ book.page_count }}</span>
              </div>
            </div>
          </div>

          <EventTimeline :events="events ?? []" />

          <div class="book-actions">
            <button @click="handleEdit" class="btn-primary">
              Edit Book
            </button>
          </div>
        </div>
      </div>
    </div>

    <BookSearchModal
        v-if="showSearchModal"
        @close="handleSearchModalClose"
        @select="handleBookSelected"
    />

  </div>
</template>

<style scoped>
.book-detail-page {
  min-height: 100vh;
  background-color: var(--color-bg);
}

.book-detail {
  background: transparent;
  border-radius: var(--border-radius);
  box-shadow: none;
  overflow: hidden;
  max-width: 100%;
}

.book-header {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  column-gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  background: transparent;
  align-items: flex-start;
  width: 100%;
  max-width: 100%;
}

.book-cover-section {
  flex-shrink: 0;
  max-width: 100%;
}

.book-cover-large {
  width: min(240px, 100%);
  max-width: 100%;
  height: auto;
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  display: block;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.book-cover-placeholder {
  aspect-ratio: 2 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 14px;
  text-align: center;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.book-info {
  display: flex;
  flex-direction: column;
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
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
  justify-content: flex-start;
}

.book-actions button {
  flex: 0 0 auto;
  min-width: 140px;
  max-width: 220px;
  width: auto;
}

.book-status-section {
  margin-bottom: var(--spacing-lg);
  padding: 0;
  background-color: transparent;
  border: none;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
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
  background: transparent;
}

.book-description {
  margin-bottom: var(--spacing-xl);
  position: relative;
}

.book-description h2 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

.book-description .description-text {
  line-height: 1.6;
  color: var(--color-text);
  white-space: pre-wrap;
  word-break: break-word;
  overflow-wrap: anywhere;
  overflow: hidden;
  position: relative;
  max-height: none;
  transition: max-height 240ms ease;
  will-change: max-height;
}

.book-description .description-text.clamped {
  opacity: 1;
}

.book-description .description-text.clamped::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1.8rem;
  pointer-events: none;
  background: linear-gradient(
    to bottom,
    rgba(0, 0, 0, 0),
    var(--color-bg)
  );
}

@supports (mask-image: linear-gradient(#000, transparent)) {
  .book-description .description-text.clamped {
    mask-image: linear-gradient(180deg, #000 0%, #000 70%, transparent 100%);
    -webkit-mask-image: linear-gradient(180deg, #000 0%, #000 70%, transparent 100%);
    mask-size: 100% 100%;
    -webkit-mask-size: 100% 100%;
    mask-repeat: no-repeat;
    -webkit-mask-repeat: no-repeat;
  }

  .book-description .description-text.clamped::after {
    content: none;
  }
}

.description-toggle {
  margin-top: var(--spacing-xs);
  padding: 0;
  border: none;
  background: none;
  color: var(--color-primary);
  font-size: 0.95rem;
  cursor: pointer;
}

.description-toggle:hover {
  text-decoration: underline;
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
  .book-detail-page {
    border-radius: 0;
    min-height: 100%;
  }

  .book-detail {
    border: none;
    border-radius: 0;
    box-shadow: none;
    background: transparent;
  }

  .book-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--spacing-lg);
    flex-wrap: wrap;
  }

  .book-cover-section {
    display: flex;
    justify-content: center;
    width: 100%;
    margin-bottom: var(--spacing-lg);
  }

  .book-cover-large {
    width: min(200px, 100%);
    height: auto;
  }

  .book-info h1 {
    font-size: 1.5rem;
  }

  .book-info {
    width: 100%;
  }

.book-actions {
    flex-direction: column;
  }

  .book-actions button {
    width: 100%;
    flex: 0 0 auto;
  }

  .book-status-section {
    align-items: center;
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
