<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'
import draggable from 'vuedraggable'
import { useRouter } from 'vue-router'
import { createBook, getListBooks, getLists, reorderListItem } from '../api/books'
import { getMediaUrl } from '../api/client'
import BookCard from '../components/BookCard.vue'
import BookSearchModal from '../components/BookSearchModal.vue'
import NavigationBar from '../components/NavigationBar.vue'
import { ReadingStatus, type PaginatedBooks, type GoogleBookResult, type Book, type BookList } from '../api/types'
import { useCachedQuery } from '../composables/useCachedQuery'
import { cacheKeys } from '../cache/keys'
import { cacheInvalidateByPrefix } from '../cache/store'

const currentPage = ref(1)
const pageSize = ref(30)
const router = useRouter()
const accumulatedBooks = ref<Book[]>([])
const isLoadingMore = ref(false)

const showSearchModal = ref(false)
const addingBook = ref(false)

const filterStatus = ref<ReadingStatus | ''>('')
const searchQuery = ref('')
const showFilterDropdown = ref(false)
const shelfFilter = ref<'to-read' | 'finished'>('to-read')
const showShelfMenu = ref(false)
const activeListId = ref<number | null>(null)

const { data: listsData } = useCachedQuery<BookList[]>(
  cacheKeys.lists(),
  () => getLists()
)

const lists = computed(() => listsData.value ?? [])

watch(lists, (newLists) => {
  if (newLists.length && !activeListId.value) {
    setActiveListForShelf()
  }
}, { immediate: true })

const {
  data: booksData,
  error: booksError,
  refresh: refreshBooks,
} = useCachedQuery<PaginatedBooks>(
  computed(() =>
    activeListId.value
      ? cacheKeys.listBooks(activeListId.value, currentPage.value, pageSize.value)
      : ''
  ),
  () => getListBooks(activeListId.value!, currentPage.value, pageSize.value),
  { enabled: computed(() => activeListId.value !== null) }
)

const error = computed(() => {
  const e = booksError.value
  if (!e) return ''
  if (e instanceof Error) return e.message
  return 'Failed to load books. Please try again.'
})

// Load saved view mode from localStorage, default to 'list'
const savedViewMode = localStorage.getItem('booksViewMode') as 'list' | 'grid' | null
const viewMode = ref<'list' | 'grid'>(savedViewMode || 'list')

// Watch viewMode and save to localStorage whenever it changes
watch(viewMode, (newMode) => {
  localStorage.setItem('booksViewMode', newMode)
})

watch(booksData, (next) => {
  if (!next) return
  if (next.page === 1) {
    accumulatedBooks.value = [...next.items]
  } else {
    const seen = new Set(accumulatedBooks.value.map(b => b.id))
    const additions = next.items.filter(b => !seen.has(b.id))
    accumulatedBooks.value = [...accumulatedBooks.value, ...additions]
  }
  isLoadingMore.value = false
  nextTick(() => {
    if (sentinelObserver && sentinelEl.value) {
      sentinelObserver.unobserve(sentinelEl.value)
      sentinelObserver.observe(sentinelEl.value)
    }
  })
})

const hasMore = computed(() =>
  Boolean(booksData.value) && currentPage.value < (booksData.value?.pages ?? 1)
)

const filteredBooks = computed(() => {
  if (!booksData.value && accumulatedBooks.value.length === 0) return []

  let books = accumulatedBooks.value

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

const currentlyReadingBooks = computed(() =>
  filteredBooks.value.filter(book => book.user_status?.status === ReadingStatus.STARTED)
)
const toReadBooks = computed(() =>
  filteredBooks.value.filter(book => book.user_status?.status !== ReadingStatus.STARTED)
)

const gridBooks = ref<Book[]>([])
const gridCurrentlyReading = ref<Book[]>([])
const gridToRead = ref<Book[]>([])
const isDragging = ref(false)
const lastDragTime = ref(0)
watch(
  filteredBooks,
  (next) => {
    gridBooks.value = [...next]
    gridCurrentlyReading.value = next.filter(
      book => book.user_status?.status === ReadingStatus.STARTED
    )
    gridToRead.value = next.filter(book => book.user_status?.status !== ReadingStatus.STARTED)
  },
  { immediate: true }
)

function getShelfListName(): string {
  return shelfFilter.value === 'to-read' ? 'To Read' : 'Finished'
}

function setActiveListForShelf() {
  const targetName = getShelfListName()
  const match = lists.value.find(list => list.name === targetName) || null
  activeListId.value = match ? match.id : null
}

async function loadBooks() {
  await refreshBooks()
}

function resetPagination() {
  currentPage.value = 1
  accumulatedBooks.value = []
}

async function loadMore() {
  if (isLoadingMore.value || !hasMore.value) return
  isLoadingMore.value = true
  currentPage.value += 1
}

let sentinelObserver: IntersectionObserver | null = null
const sentinelEl = ref<HTMLElement | null>(null)

function setupObserver() {
  if (sentinelObserver || !sentinelEl.value) return
  sentinelObserver = new IntersectionObserver((entries) => {
    for (const entry of entries) {
      if (entry.isIntersecting) loadMore()
    }
  }, { rootMargin: '400px 0px' })
  sentinelObserver.observe(sentinelEl.value)
}

watch(sentinelEl, () => {
  if (sentinelObserver) {
    sentinelObserver.disconnect()
    sentinelObserver = null
  }
  nextTick(() => setupObserver())
})

onMounted(() => nextTick(() => setupObserver()))
onBeforeUnmount(() => {
  sentinelObserver?.disconnect()
  sentinelObserver = null
})

function handleAddBook() {
  showSearchModal.value = true
}

function handleSearchModalClose() {
  if (addingBook.value) return
  showSearchModal.value = false
}

async function handleBookSelected(book: GoogleBookResult) {
  if (addingBook.value) return
  addingBook.value = true
  try {
    await createBook({
      title: book.title,
      author: book.author,
      isbn: book.isbn || undefined,
      description: book.description || undefined,
      published_date: book.published_date || undefined,
      page_count: book.page_count ?? undefined,
      cover_image_url: book.thumbnail || undefined,
    })
    await cacheInvalidateByPrefix('lists:')
    resetPagination()
    await refreshBooks()
    showSearchModal.value = false
  } catch (err: any) {
    console.error('Failed to add book:', err)
    alert(err.response?.data?.detail || 'Failed to add book. Please try again.')
  } finally {
    addingBook.value = false
  }
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

function toggleFilterDropdown() {
  showFilterDropdown.value = !showFilterDropdown.value
}

const shelfLabel = computed(() => (shelfFilter.value === 'to-read' ? 'To Read' : 'Finished'))

function toggleShelfMenu() {
  showShelfMenu.value = !showShelfMenu.value
}

function setShelfFilter(next: 'to-read' | 'finished') {
  shelfFilter.value = next
  if (filterStatus.value) {
    filterStatus.value = ''
  }
  showShelfMenu.value = false
  resetPagination()
  setActiveListForShelf()
  loadBooks()
}

function handleDragStart() {
  isDragging.value = true
}

async function handleDragEndForList(
  list: Book[],
  event: { newIndex?: number; oldIndex?: number } | null
) {
  isDragging.value = false
  lastDragTime.value = Date.now()

  if (!event || event.newIndex === undefined || event.oldIndex === undefined) {
    return
  }
  if (event.newIndex === event.oldIndex) {
    return
  }
  if (!activeListId.value) {
    return
  }
  if (searchQuery.value.trim() || filterStatus.value) {
    return
  }

  const movedBook = list[event.newIndex]
  if (!movedBook) return
  const beforeBook = event.newIndex > 0 ? list[event.newIndex - 1] : null
  const afterBook = event.newIndex < list.length - 1 ? list[event.newIndex + 1] : null

  try {
    await reorderListItem(activeListId.value, {
      moved_book_id: movedBook.id,
      before_book_id: beforeBook?.id ?? null,
      after_book_id: afterBook?.id ?? null,
    })
    accumulatedBooks.value =
      shelfFilter.value === 'to-read'
        ? [...gridCurrentlyReading.value, ...gridToRead.value]
        : [...gridBooks.value]
  } catch (err: any) {
    console.error('Failed to reorder books:', err)
  }
}

function handleCoverClick(bookId: number) {
  if (isDragging.value) return
  if (Date.now() - lastDragTime.value < 200) return
  router.push({ name: 'book-detail', params: { id: bookId } })
}

function showProgressBadge(book: Book): boolean {
  return (
    book.user_status?.status === ReadingStatus.STARTED &&
    Boolean(book.page_count) &&
    book.user_status?.current_page !== null &&
    book.user_status?.current_page !== undefined
  )
}

function getProgressPercent(book: Book): number {
  const pageCount = book.page_count ?? 0
  const currentPage = book.user_status?.current_page ?? 0
  if (pageCount <= 0) return 0
  const percent = Math.round((currentPage / pageCount) * 100)
  return Math.min(100, Math.max(0, percent))
}

</script>

<template>
  <div class="books-view">
    <NavigationBar @add-book="handleAddBook" />

    <div class="container">

      <div v-if="error" class="error">
        {{ error }}
      </div>

      <div class="search-header">
        <div class="search-bar">
          <svg class="search-icon" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <circle cx="11" cy="11" r="8"></circle>
            <path d="m21 21-4.35-4.35"></path>
          </svg>
          <input
            v-model="searchQuery"
            type="text"
            placeholder="Search for words or #tags"
            class="search-input"
          />
        </div>

        <div class="search-actions">
          <div class="filter-dropdown-wrapper">
            <button @click="toggleFilterDropdown" class="filter-btn" title="Filter options">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polygon points="22 3 2 3 10 12.46 10 19 14 21 14 12.46 22 3"></polygon>
              </svg>
            </button>

            <div v-if="showFilterDropdown" class="filter-dropdown">
              <div class="filter-dropdown-section">
                <label class="filter-dropdown-label">Status</label>
                <select v-model="filterStatus" class="filter-dropdown-select" @change="showFilterDropdown = false">
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
          </div>

          <div class="view-toggle">
            <button
              @click="viewMode = 'list'"
              :class="['view-btn', { active: viewMode === 'list' }]"
              title="List view"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <line x1="8" y1="6" x2="21" y2="6"></line>
                <line x1="8" y1="12" x2="21" y2="12"></line>
                <line x1="8" y1="18" x2="21" y2="18"></line>
                <line x1="3" y1="6" x2="3.01" y2="6"></line>
                <line x1="3" y1="12" x2="3.01" y2="12"></line>
                <line x1="3" y1="18" x2="3.01" y2="18"></line>
              </svg>
            </button>

            <button
              @click="viewMode = 'grid'"
              :class="['view-btn', { active: viewMode === 'grid' }]"
              title="Grid view"
            >
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <rect x="3" y="3" width="7" height="7"></rect>
                <rect x="14" y="3" width="7" height="7"></rect>
                <rect x="14" y="14" width="7" height="7"></rect>
                <rect x="3" y="14" width="7" height="7"></rect>
              </svg>
            </button>
          </div>
        </div>
      </div>

      <div v-if="filterStatus" class="active-filters">
        <div class="filter-tag">
          Status: {{ getStatusLabel(filterStatus) }}
          <button @click="filterStatus = ''" class="filter-tag-remove">×</button>
        </div>
      </div>

      <div v-if="booksData && filteredBooks.length === 0" class="empty-state">
        <p v-if="searchQuery || filterStatus">No books match your filters.</p>
        <p v-else>No books yet. Add your first book to get started!</p>
      </div>

      <template v-if="viewMode === 'grid'">
        <template v-if="shelfFilter === 'to-read'">
          <section v-if="gridCurrentlyReading.length" class="shelf-section">
            <h2 class="shelf-section-title">Currently Reading</h2>
            <draggable
              class="books-container books-grid sectioned"
              :list="gridCurrentlyReading"
              item-key="id"
              :animation="150"
              :delay="120"
              :delay-on-touch-only="true"
              :disabled="Boolean(searchQuery.trim()) || Boolean(filterStatus)"
              ghost-class="grid-ghost"
              drag-class="grid-drag"
              chosen-class="grid-chosen"
              @start="handleDragStart"
              @end="handleDragEndForList(gridCurrentlyReading, $event)"
            >
              <template #item="{ element: book }">
                <div class="grid-item">
                  <button
                    type="button"
                    class="grid-cover-link"
                    @click="handleCoverClick(book.id)"
                  >
                    <span
                      v-if="showProgressBadge(book)"
                      class="grid-progress-badge"
                    >
                      {{ getProgressPercent(book) }}%
                    </span>
                    <img
                      v-if="book.cover_thumbnail_url || book.cover_image_url"
                      :src="getMediaUrl(book.cover_thumbnail_url || book.cover_image_url)"
                      :alt="book.title"
                      :title="book.title + ' by ' + book.author"
                      class="grid-cover"
                    />
                    <div
                      v-else
                      class="grid-cover-placeholder"
                      :title="book.title + ' by ' + book.author"
                    >
                      <div class="grid-no-cover-text">{{ book.title }}</div>
                    </div>
                  </button>
                </div>
              </template>
            </draggable>
          </section>

          <section v-if="gridToRead.length" class="shelf-section">
            <h2 class="shelf-section-title">To Read</h2>
            <draggable
              class="books-container books-grid sectioned"
              :list="gridToRead"
              item-key="id"
              :animation="150"
              :delay="120"
              :delay-on-touch-only="true"
              :disabled="Boolean(searchQuery.trim()) || Boolean(filterStatus)"
              ghost-class="grid-ghost"
              drag-class="grid-drag"
              chosen-class="grid-chosen"
              @start="handleDragStart"
              @end="handleDragEndForList(gridToRead, $event)"
            >
              <template #item="{ element: book }">
                <div class="grid-item">
                  <button
                    type="button"
                    class="grid-cover-link"
                    @click="handleCoverClick(book.id)"
                  >
                    <img
                      v-if="book.cover_thumbnail_url || book.cover_image_url"
                      :src="getMediaUrl(book.cover_thumbnail_url || book.cover_image_url)"
                      :alt="book.title"
                      :title="book.title + ' by ' + book.author"
                      class="grid-cover"
                    />
                    <div
                      v-else
                      class="grid-cover-placeholder"
                      :title="book.title + ' by ' + book.author"
                    >
                      <div class="grid-no-cover-text">{{ book.title }}</div>
                    </div>
                  </button>
                </div>
              </template>
            </draggable>
          </section>
        </template>

        <draggable
          v-else
          class="books-container books-grid"
          :list="gridBooks"
          item-key="id"
          :animation="150"
          :delay="120"
          :delay-on-touch-only="true"
          :disabled="Boolean(searchQuery.trim()) || Boolean(filterStatus)"
          ghost-class="grid-ghost"
          drag-class="grid-drag"
          chosen-class="grid-chosen"
          @start="handleDragStart"
          @end="handleDragEndForList(gridBooks, $event)"
        >
          <template #item="{ element: book }">
            <div class="grid-item">
              <button
                type="button"
                class="grid-cover-link"
                @click="handleCoverClick(book.id)"
              >
                <img
                  v-if="book.cover_thumbnail_url || book.cover_image_url"
                  :src="getMediaUrl(book.cover_thumbnail_url || book.cover_image_url)"
                  :alt="book.title"
                  :title="book.title + ' by ' + book.author"
                  class="grid-cover"
                />
                <div
                  v-else
                  class="grid-cover-placeholder"
                  :title="book.title + ' by ' + book.author"
                >
                  <div class="grid-no-cover-text">{{ book.title }}</div>
                </div>
              </button>
            </div>
          </template>
        </draggable>
      </template>

      <div v-else class="books-container books-list">
        <template v-if="shelfFilter === 'to-read'">
          <section v-if="currentlyReadingBooks.length" class="shelf-section">
            <h2 class="shelf-section-title">Currently Reading</h2>
            <div
              v-for="book in currentlyReadingBooks"
              :key="book.id"
            >
              <BookCard :book="book" />
            </div>
          </section>
          <section v-if="toReadBooks.length" class="shelf-section">
            <h2 class="shelf-section-title">To Read</h2>
            <div
              v-for="book in toReadBooks"
              :key="book.id"
            >
              <BookCard :book="book" />
            </div>
          </section>
        </template>
        <div
          v-else
          v-for="book in filteredBooks"
          :key="book.id"
        >
          <BookCard :book="book" />
        </div>
      </div>

      <div
        v-if="hasMore || isLoadingMore"
        ref="sentinelEl"
        class="infinite-sentinel"
      >
        <span v-if="isLoadingMore" class="infinite-loading">Loading more…</span>
      </div>
    </div>

    <BookSearchModal
      v-if="showSearchModal"
      @close="handleSearchModalClose"
      @select="handleBookSelected"
    />

    <div class="bottom-bar">
      <div v-if="showShelfMenu" class="bottom-menu" role="menu">
        <button
          type="button"
          role="menuitemradio"
          :aria-checked="shelfFilter === 'to-read'"
          :class="['bottom-menu-item', { active: shelfFilter === 'to-read' }]"
          @click="setShelfFilter('to-read')"
        >
          To Read
        </button>
        <button
          type="button"
          role="menuitemradio"
          :aria-checked="shelfFilter === 'finished'"
          :class="['bottom-menu-item', { active: shelfFilter === 'finished' }]"
          @click="setShelfFilter('finished')"
        >
          Finished
        </button>
      </div>

      <button
        type="button"
        class="bottom-bar-button"
        @click="toggleShelfMenu"
        :aria-expanded="showShelfMenu"
      >
        <span class="bar-text">{{ shelfLabel }}</span>
        <span class="bar-arrow" aria-hidden="true">
          <svg viewBox="0 0 24 24" role="presentation" focusable="false">
            <path d="M12 5l6.5 7.2a1.1 1.1 0 0 1-1.7 1.3L12 8.9l-4.8 4.6a1.1 1.1 0 0 1-1.6-1.5L12 5z"/>
          </svg>
        </span>
      </button>
    </div>
  </div>
</template>

<style scoped>
.books-view {
  min-height: 100svh;
  padding-bottom: 112px;
  box-sizing: border-box;
  background-color: var(--color-bg);
}

.books-view :deep(.navbar) {
  z-index: 200;
}

.bottom-bar {
  position: fixed;
  left: 50%;
  bottom: calc(14px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  width: min(92vw, 420px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.bottom-bar-button {
  width: 100%;
  height: 58px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #fff;
  border: 2px solid #1b2639;
  border-radius: 999px;
  box-shadow: 0 10px 26px rgba(27, 38, 57, 0.18);
  font-family: 'Inter', 'Segoe UI', sans-serif;
  font-size: 1.2rem;
  font-weight: 700;
  color: #1b2639;
  gap: 10px;
  padding: 0 22px;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.bottom-bar-button:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 28px rgba(27, 38, 57, 0.24);
}

.bottom-bar-button:focus-visible {
  outline: 2px solid #1b2639;
  outline-offset: 3px;
}

.bottom-menu {
  position: absolute;
  bottom: calc(100% + 10px);
  left: 50%;
  transform: translateX(-50%);
  width: min(86vw, 360px);
  background: #fff;
  border: 2px solid #1b2639;
  border-radius: 18px;
  box-shadow: 0 12px 30px rgba(27, 38, 57, 0.2);
  padding: 8px;
  display: flex;
  gap: 8px;
}

.bottom-menu-item {
  flex: 1;
  border: 1px solid #1b2639;
  background: transparent;
  color: #1b2639;
  font-weight: 700;
  font-size: 1rem;
  padding: 10px 12px;
  border-radius: 999px;
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.bottom-menu-item.active {
  background: #1b2639;
  color: #fff;
}

.bar-text {
  display: inline-flex;
  align-items: baseline;
  gap: 0.12em;
  letter-spacing: 0.03em;
  text-transform: uppercase;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
}

.bar-arrow {
  width: 20px;
  height: 20px;
  display: inline-flex;
  align-items: center;
}

.bar-arrow svg {
  width: 100%;
  height: 100%;
  fill: currentColor;
}

.search-header {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  align-items: center;
  justify-content: space-between;
  border-radius: var(--border-radius);
  max-width: 100%;
  overflow: visible;
}

.search-bar {
  flex: 1 1 auto;
  min-width: 0;
  max-width: 500px;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background-color: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  transition: border-color 0.15s ease, box-shadow 0.15s ease;
}

.search-bar:hover {
  border-color: var(--color-text-secondary);
}

.search-bar:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(88, 86, 214, 0.35);
}

.search-icon {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.search-actions {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 0 var(--spacing-xs);
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border: none;
}

.filter-dropdown-wrapper {
  position: relative;
}

.filter-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-sm);
  background: transparent;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.15s ease;
  min-width: 36px;
  min-height: 36px;
}

.filter-btn:hover {
  color: var(--color-text);
  background-color: var(--color-bg);
  border-color: var(--color-text-secondary);
}

.view-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  overflow: hidden;
  background-color: var(--color-bg-card);
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-sm);
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.15s ease;
  min-width: 36px;
  min-height: 36px;
  position: relative;
}

.view-btn:not(:last-child)::after {
  content: '';
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 60%;
  width: 1px;
  background-color: var(--color-border);
}

.view-btn:hover:not(.active) {
  color: var(--color-text);
  background-color: var(--color-bg);
}

.filter-dropdown {
  position: absolute;
  top: calc(100% + 4px);
  right: 0;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: var(--modal-shadow);
  padding: var(--spacing-md);
  min-width: 200px;
  z-index: 100;
}

.filter-dropdown-section {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.filter-dropdown-label {
  font-size: 13px;
  font-weight: 600;
  color: var(--color-text);
  margin-bottom: 0;
}

.filter-dropdown-select {
  width: 100%;
  padding: var(--spacing-xs) var(--spacing-sm);
  font-size: 14px;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background-color: var(--color-bg-card);
  color: var(--color-text);
}

.view-btn.active {
  background-color: var(--color-primary);
  color: white;
}

.view-btn.active::after {
  display: none;
}

.view-btn.active:hover {
  background-color: var(--color-primary-hover);
  color: white;
}

.active-filters {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
  flex-wrap: wrap;
}

.filter-tag {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-sm);
  background-color: var(--color-primary);
  color: white;
  border-radius: var(--border-radius);
  font-size: 13px;
  font-weight: 500;
}

.filter-tag-remove {
  background: none;
  border: none;
  color: white;
  cursor: pointer;
  padding: 0;
  font-size: 20px;
  line-height: 1;
  font-weight: 300;
  opacity: 0.8;
  transition: opacity 0.15s ease;
}

.filter-tag-remove:hover {
  opacity: 1;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

.books-container {
  margin-top: var(--spacing-lg);
  overflow-x: clip;
  overflow-y: visible;
}

.books-container.sectioned {
  margin-top: 0;
}

.shelf-section {
  margin-top: var(--spacing-lg);
}

.shelf-section:first-child {
  margin-top: 0;
}

.shelf-section-title {
  margin: 0 0 var(--spacing-sm);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.books-list {
  display: flex;
  flex-direction: column;
}

.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: var(--spacing-md);
  align-items: center;
  width: 100%;
  max-width: 100%;
  padding-top: 6px;
  padding-bottom: var(--spacing-sm);
  overflow-x: clip;
  overflow-y: visible;
}

.grid-ghost {
  opacity: 0;
}

.grid-drag,
.grid-chosen {
  opacity: 1 !important;
}

.grid-item {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  overflow: visible;
}

.grid-cover-link {
  padding: 0;
  border: none;
  background: transparent;
  text-decoration: none;
  display: block;
  cursor: grab;
  width: 100%;
  text-align: left;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
  position: relative;
}

.grid-cover {
  width: 100%;
  max-width: 100%;
  height: auto;
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: transform 0.2s ease;
  box-shadow: var(--shadow);
  display: block;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.grid-cover:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
}

.books-grid .sortable-ghost .grid-cover,
.books-grid .sortable-ghost .grid-cover-placeholder,
.books-grid .sortable-chosen .grid-cover,
.books-grid .sortable-chosen .grid-cover-placeholder,
.books-grid .sortable-drag .grid-cover,
.books-grid .sortable-drag .grid-cover-placeholder {
  transform: none;
  box-shadow: var(--shadow);
}

.grid-cover-placeholder {
  width: 100%;
  max-width: 100%;
  aspect-ratio: 2/3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  transition: transform 0.2s ease;
  box-shadow: var(--shadow);
  padding: var(--spacing-md);
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
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

.grid-progress-badge {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 2;
  background: rgba(20, 24, 31, 0.85);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 7px;
  border-radius: 999px;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
  pointer-events: none;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
}

.grid-cover-link:hover .grid-progress-badge {
  transform: translateY(-4px);
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.25);
}

.infinite-sentinel {
  display: flex;
  justify-content: center;
  align-items: center;
  padding: var(--spacing-lg) 0;
  min-height: 48px;
}

.infinite-loading {
  color: var(--color-text-secondary);
  font-size: 14px;
}

@media (max-width: 768px) {
  .search-header {
    flex-wrap: wrap;
  }

  .search-bar {
    flex: 1 1 100%;
    max-width: 100%;
    order: -1;
  }

  /* Prevent iOS Safari zooming inputs with font-size under 16px. */
  .search-input {
    font-size: 16px;
  }

  .filter-btn {
    flex: 1;
  }

  .view-toggle {
    flex: 1;
  }

  .view-btn {
    flex: 1;
  }

  .books-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: var(--spacing-md);
  }
}

@media (max-width: 480px) {
  .books-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: var(--spacing-sm);
  }
}

@media (min-width: 600px) {
  .books-view {
    padding-bottom: 120px;
  }
}
</style>
