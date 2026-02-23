<script setup lang="ts">
import {computed, ref, onMounted, onBeforeUnmount, watch, nextTick} from 'vue'
import {useRouter, useRoute} from 'vue-router'
import {getBook, setReadingStatus, deleteBook, getBookEvents, addBookProgress} from '../api/books'
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
const notesDraft = ref('')
const notesSaving = ref(false)
const progressDraft = ref<string | number>('')
const progressSaving = ref(false)
const progressEditing = ref(false)
const showEditModal = ref(false)
const showSearchModal = ref(false)
const showFormModal = ref(false)
const showStatusSheet = ref(false)
const prefilledBookData = ref<GoogleBookResult | null>(null)
const descriptionRef = ref<HTMLElement | null>(null)
const descriptionExpanded = ref(false)
const showDescriptionToggle = ref(false)
const descriptionMaxHeight = ref<string>('')

const defaultPalette = {
  accent1: '255 200 140',
  accent2: '188 120 255',
  accent3: '120 160 255',
}

const coverPalette = ref({...defaultPalette})

const coverUrl = computed(() => {
  if (!book.value) return ''
  const rawUrl = book.value.cover_image_url || book.value.cover_thumbnail_url
  return rawUrl ? getMediaUrl(rawUrl) : ''
})

const pageStyle = computed(() => {
  return {
    '--cover-accent-1': coverPalette.value.accent1,
    '--cover-accent-2': coverPalette.value.accent2,
    '--cover-accent-3': coverPalette.value.accent3,
  }
})

onMounted(() => {
  loadBook()
  window.addEventListener('resize', updateDescriptionToggle)
})

onBeforeUnmount(() => {
  window.removeEventListener('resize', updateDescriptionToggle)
})

watch(
  () => book.value?.description,
  async () => {
    descriptionExpanded.value = false
    await nextTick()
    updateDescriptionToggle()
  },
)

function getClampHeight(el: HTMLElement) {
  const computedStyles = window.getComputedStyle(el)
  const lineHeight = parseFloat(computedStyles.lineHeight)
  if (Number.isFinite(lineHeight)) {
    return Math.round(lineHeight * 3)
  }
  const fontSize = parseFloat(computedStyles.fontSize) || 16
  return Math.round(fontSize * 1.6 * 3)
}

function measureExpandedHeight(el: HTMLElement) {
  const previousStyles = {
    overflow: el.style.overflow,
    maxHeight: el.style.maxHeight,
  }

  el.style.overflow = 'visible'
  el.style.maxHeight = 'none'

  const height = el.scrollHeight

  el.style.overflow = previousStyles.overflow
  el.style.maxHeight = previousStyles.maxHeight

  return height
}

function updateDescriptionToggle() {
  const el = descriptionRef.value
  if (!el) {
    showDescriptionToggle.value = false
    return
  }

  const clampHeight = getClampHeight(el)
  showDescriptionToggle.value = el.scrollHeight > clampHeight + 1

  if (!descriptionExpanded.value) {
    descriptionMaxHeight.value = `${clampHeight}px`
  } else {
    descriptionMaxHeight.value = `${measureExpandedHeight(el)}px`
  }
}

function toggleDescription() {
  const el = descriptionRef.value
  if (!el) return

  const clampHeight = getClampHeight(el)

  if (!descriptionExpanded.value) {
    const expandedHeight = measureExpandedHeight(el)
    descriptionMaxHeight.value = `${clampHeight}px`
    void el.offsetHeight
    descriptionMaxHeight.value = `${expandedHeight}px`
    descriptionExpanded.value = true
    return
  }

  const currentHeight = measureExpandedHeight(el)
  descriptionMaxHeight.value = `${currentHeight}px`
  void el.offsetHeight
  descriptionMaxHeight.value = `${clampHeight}px`
  descriptionExpanded.value = false
}

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
    notesDraft.value = book.value.user_status?.notes ?? ''
    progressDraft.value = book.value.user_status?.current_page?.toString() ?? ''
    progressEditing.value = false
    await loadEvents(bookId)
  } catch (err: any) {
    console.error('Failed to load book:', err)
    error.value = err.response?.data?.detail || 'Failed to load book. Please try again.'
  } finally {
    loading.value = false
    await nextTick()
    updateDescriptionToggle()
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
const canUpdateProgress = computed(() => book.value?.user_status?.status === ReadingStatus.STARTED)

function normalizeNotes(value: string): string | null {
  return value === '' ? null : value
}

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

const notesDirty = computed(() => {
  if (!book.value) return false
  const currentNotes = book.value.user_status?.notes ?? null
  return normalizeNotes(notesDraft.value) !== currentNotes
})

async function handleStartReading() {
  if (!book.value) return
  updatingStatus.value = true

  try {
    await setReadingStatus(book.value.id, {status: ReadingStatus.STARTED})
    await loadBook()
    showStatusSheet.value = false
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
    showStatusSheet.value = false
  } catch (error) {
    console.error('Failed to finish reading:', error)
    alert('Failed to finish reading')
  } finally {
    updatingStatus.value = false
  }
}

async function handleSaveNotes() {
  if (!book.value) return
  if (!notesDirty.value) return

  notesSaving.value = true
  try {
    const status = book.value.user_status?.status ?? ReadingStatus.WANT_TO_READ
    const updatedStatus = await setReadingStatus(book.value.id, {
      status,
      notes: notesDraft.value,
    })
    book.value.user_status = updatedStatus
    notesDraft.value = updatedStatus.notes ?? ''
    await loadEvents(book.value.id)
  } catch (error) {
    console.error('Failed to save notes:', error)
    alert('Failed to save notes')
  } finally {
    notesSaving.value = false
  }
}

async function handleSaveProgress(): Promise<boolean> {
  if (!book.value) return false
  if (!canUpdateProgress.value) return false

  const rawProgress = progressDraft.value
  const trimmed =
      typeof rawProgress === 'string'
        ? rawProgress.trim()
        : String(rawProgress ?? '').trim()
  if (!trimmed) {
    alert('Please enter a page number.')
    return false
  }

  const page = Number.parseInt(trimmed, 10)
  if (Number.isNaN(page) || page < 0) {
    alert('Please enter a valid page number.')
    return false
  }

  progressSaving.value = true
  try {
    const updatedStatus = await addBookProgress(book.value.id, {page})
    book.value.user_status = updatedStatus
    progressDraft.value = updatedStatus.current_page?.toString() ?? ''
    await loadEvents(book.value.id)
    return true
  } catch (error) {
    console.error('Failed to save progress:', error)
    alert('Failed to save progress')
    return false
  } finally {
    progressSaving.value = false
  }
}

async function handleProgressAction() {
  if (!progressEditing.value) {
    progressDraft.value = book.value?.user_status?.current_page?.toString() ?? ''
    progressEditing.value = true
    return
  }
  if (!canUpdateProgress.value || progressSaving.value) return
  const saved = await handleSaveProgress()
  if (saved) {
    progressEditing.value = false
  }
}

function handleCancelProgress() {
  progressDraft.value = book.value?.user_status?.current_page?.toString() ?? ''
  progressEditing.value = false
}

function handleProgressFocus(event: FocusEvent) {
  const target = event.target as HTMLInputElement | null
  target?.select()
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

function mixColorChannel(channel: number, mix: number) {
  return Math.round(channel * (1 - mix) + 255 * mix)
}

function mixWithBlack(channel: number, mix: number) {
  return Math.round(channel * (1 - mix))
}

async function updateCoverPalette(url: string) {
  try {
    const image = new Image()
    image.crossOrigin = 'anonymous'
    image.src = url
    await new Promise<void>((resolve, reject) => {
      image.onload = () => resolve()
      image.onerror = () => reject(new Error('Failed to load cover image'))
    })

    const canvas = document.createElement('canvas')
    const size = 24
    canvas.width = size
    canvas.height = size
    const context = canvas.getContext('2d')
    if (!context) {
      coverPalette.value = {...defaultPalette}
      return
    }

    context.drawImage(image, 0, 0, size, size)
    const {data} = context.getImageData(0, 0, size, size)
    let totalR = 0
    let totalG = 0
    let totalB = 0
    let count = 0

    for (let i = 0; i < data.length; i += 4) {
      const alpha = data[i + 3] ?? 0
      if (alpha < 16) continue
      totalR += data[i] ?? 0
      totalG += data[i + 1] ?? 0
      totalB += data[i + 2] ?? 0
      count += 1
    }

    if (!count) {
      coverPalette.value = {...defaultPalette}
      return
    }

    const avgR = Math.round(totalR / count)
    const avgG = Math.round(totalG / count)
    const avgB = Math.round(totalB / count)

    const lighter = {
      r: mixColorChannel(avgR, 0.28),
      g: mixColorChannel(avgG, 0.28),
      b: mixColorChannel(avgB, 0.28),
    }

    const darker = {
      r: mixWithBlack(avgR, 0.35),
      g: mixWithBlack(avgG, 0.35),
      b: mixWithBlack(avgB, 0.35),
    }

    coverPalette.value = {
      accent1: `${avgR} ${avgG} ${avgB}`,
      accent2: `${lighter.r} ${lighter.g} ${lighter.b}`,
      accent3: `${darker.r} ${darker.g} ${darker.b}`,
    }
  } catch (error) {
    console.warn('Cover palette fallback:', error)
    coverPalette.value = {...defaultPalette}
  }
}

watch(
  () => coverUrl.value,
  async (url) => {
    if (!url) {
      coverPalette.value = {...defaultPalette}
      return
    }
    await updateCoverPalette(url)
  },
  {immediate: true},
)
</script>

<template>
  <div class="book-detail-page" :style="pageStyle">
    <NavigationBar @add-book="handleAddBook"/>

    <div class="container">
      <div class="breadcrumb">
        <router-link to="/" class="breadcrumb-link">Books</router-link>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">
          {{ book ? book.title : 'Book details' }}
        </span>
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
              <button class="status-pill" type="button" @click="showStatusSheet = true">
                <span class="status-pill-label">{{ readingStatusLabel }}</span>
                <span class="status-pill-subtitle">{{ readingStatusSubtitle }}</span>
              </button>
            </div>

            <div class="progress-inline">
              <span class="progress-label">Progress</span>
              <div v-if="progressEditing" class="progress-row">
                <input
                  v-model="progressDraft"
                  type="number"
                  min="0"
                  inputmode="numeric"
                  pattern="[0-9]*"
                  class="progress-input"
                  :disabled="!canUpdateProgress || progressSaving"
                  placeholder="Page"
                  @focus="handleProgressFocus"
                />
                <span v-if="book.page_count" class="progress-total">of {{ book.page_count }}</span>
                <button
                  class="progress-button"
                  @click="handleProgressAction"
                  :disabled="!canUpdateProgress || progressSaving"
                >
                  {{ progressSaving ? 'Saving...' : 'Save' }}
                </button>
                <button
                  class="progress-button progress-cancel"
                  type="button"
                  @click="handleCancelProgress"
                  :disabled="progressSaving"
                >
                  Cancel
                </button>
              </div>
              <div v-else class="progress-row">
                <span class="progress-text">{{ progressSummary }}</span>
                <button
                  class="progress-button"
                  @click="handleProgressAction"
                  :disabled="!canUpdateProgress || progressSaving"
                >
                  Update
                </button>
              </div>
              <p v-if="!canUpdateProgress" class="progress-hint">
                Start reading to track progress.
              </p>
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

          <div class="book-notes">
            <h2>Notes</h2>
            <textarea
                v-model="notesDraft"
                class="notes-textarea"
                rows="6"
                placeholder="Add your notes about this book..."
            ></textarea>
            <div class="notes-actions">
              <button
                  class="btn-primary"
                  @click="handleSaveNotes"
                  :disabled="notesSaving || !notesDirty"
              >
                {{ notesSaving ? 'Saving...' : 'Save Notes' }}
              </button>
            </div>
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
              <div v-if="book.user_status && book.user_status.current_page !== null" class="metadata-item">
                <strong>Current page:</strong>
                {{ book.user_status.current_page }}
                <span v-if="book.page_count">/ {{ book.page_count }}</span>
              </div>
            </div>
          </div>

          <EventTimeline :events="events" />

          <div class="book-actions">
            <button @click="handleEdit" class="btn-primary">
              Edit Book
            </button>
            <button @click="handleDelete" class="btn-danger">
              Delete Book
            </button>
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

    <div v-if="showStatusSheet" class="sheet-overlay" @click.self="showStatusSheet = false">
      <div class="sheet">
        <div class="sheet-header">
          <div>
            <h3>Reading status</h3>
            <p>{{ readingStatusLabel }}</p>
          </div>
          <button class="sheet-close" type="button" @click="showStatusSheet = false">
            Close
          </button>
        </div>
        <div class="sheet-body">
          <p class="sheet-status-detail">{{ readingStatusSubtitle }}</p>
          <div class="sheet-actions">
            <button
              v-if="canStartReading"
              class="btn-secondary"
              type="button"
              @click="handleStartReading"
              :disabled="updatingStatus"
            >
              Start Reading
            </button>
            <button
              v-if="canFinishReading"
              class="btn-primary"
              type="button"
              @click="handleFinishReading"
              :disabled="updatingStatus"
            >
              Finish Reading
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-detail-page {
  position: relative;
  min-height: 100vh;
  border-radius: 28px;
  overflow: hidden;
  background:
    radial-gradient(120% 120% at 20% 15%, rgb(var(--cover-accent-1, 255 200 140) / 0.14), transparent 45%),
    radial-gradient(80% 80% at 85% 18%, rgb(var(--cover-accent-2, 188 120 255) / 0.18), transparent 50%),
    radial-gradient(100% 100% at 35% 85%, rgb(var(--cover-accent-3, 120 160 255) / 0.1), transparent 55%),
    linear-gradient(160deg, #161015 0%, #221821 45%, #1d1624 100%);
  box-shadow:
    inset 0 0 0 1px rgba(255, 255, 255, 0.03),
    0 20px 60px rgba(7, 5, 8, 0.6);
}

.book-detail-page::before {
  content: '';
  position: absolute;
  inset: -20%;
  background:
    radial-gradient(40% 40% at 30% 30%, rgb(var(--cover-accent-1, 255 178 120) / 0.2), transparent 70%),
    radial-gradient(30% 30% at 70% 40%, rgb(var(--cover-accent-2, 255 126 196) / 0.16), transparent 75%);
  filter: blur(24px);
  opacity: 0.85;
  pointer-events: none;
}

.book-detail-page::after {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, rgba(10, 8, 12, 0.2), rgba(10, 8, 12, 0.72));
  pointer-events: none;
}

.book-detail-page > * {
  position: relative;
  z-index: 1;
}

.book-detail-page :deep(.navbar) {
  background-color: transparent;
  box-shadow: none;
}

.book-detail-page :deep(.navbar-link:hover),
.book-detail-page :deep(.navbar-link-btn:hover) {
  background-color: rgba(255, 255, 255, 0.08);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.breadcrumb-link {
  color: var(--color-text);
  text-decoration: none;
  font-weight: 600;
}

.breadcrumb-link:hover {
  color: var(--color-primary);
}

.breadcrumb-separator {
  color: var(--color-text-secondary);
}

.breadcrumb-current {
  color: var(--color-text-secondary);
  max-width: min(520px, 70vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.progress-inline {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
}

.progress-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
}

.status-pill {
  border: 1px solid rgba(255, 255, 255, 0.18);
  background: rgba(12, 8, 16, 0.45);
  color: var(--color-text);
  border-radius: 999px;
  padding: 10px 16px;
  display: inline-flex;
  align-items: center;
  gap: 12px;
  width: fit-content;
  box-shadow: 0 10px 20px rgba(7, 5, 8, 0.2);
  cursor: pointer;
  transition: transform 160ms ease, border-color 160ms ease, background 160ms ease;
}

.status-pill:hover {
  transform: translateY(-1px);
  border-color: rgba(255, 255, 255, 0.32);
  background: rgba(16, 10, 22, 0.6);
}

.status-pill-label {
  font-weight: 700;
  font-size: 0.95rem;
}

.status-pill-subtitle {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
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

.book-notes {
  margin-bottom: var(--spacing-xl);
}

.book-notes h2 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

.notes-textarea {
  width: 100%;
  min-height: 120px;
  resize: vertical;
  padding: var(--spacing-sm);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.5;
}

.notes-actions {
  margin-top: var(--spacing-sm);
  display: flex;
  justify-content: flex-end;
}

.progress-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  flex-wrap: wrap;
}

.progress-input {
  width: 54px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.9rem;
  appearance: textfield;
  -moz-appearance: textfield;
}

.progress-input::-webkit-outer-spin-button,
.progress-input::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.progress-total {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.progress-text {
  color: var(--color-text);
  font-size: 0.95rem;
}

.progress-button {
  padding: 0;
  border: none;
  background: none;
  color: var(--color-primary);
  font-size: 0.9rem;
  cursor: pointer;
}

.progress-button:disabled {
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

.progress-cancel {
  color: var(--color-danger);
}

.progress-cancel:disabled {
  color: var(--color-text-secondary);
}

.progress-hint {
  margin-top: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-size: 12px;
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

.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(6, 6, 8, 0.55);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(6px);
}

.sheet {
  width: min(480px, 96vw);
  background: #1a141f;
  border-radius: 20px 20px 0 0;
  padding: var(--spacing-lg);
  box-shadow: 0 -20px 40px rgba(6, 6, 8, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.sheet-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.sheet-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.sheet-header p {
  margin: 4px 0 0 0;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.sheet-close {
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: var(--color-text);
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
}

.sheet-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.sheet-status-detail {
  margin: 0;
  font-size: 0.95rem;
  color: var(--color-text-secondary);
}

.sheet-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
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

  .progress-inline {
    align-items: center;
  }

  .progress-row {
    justify-content: center;
  }

  .status-pill {
    margin: 0 auto;
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
