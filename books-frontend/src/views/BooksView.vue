<script setup lang="ts">
import { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } from "vue";
import draggable from "vuedraggable";
import { useRouter } from "vue-router";
import { getListBooks, getLists, reorderListItem } from "../api/books";
import BookCard from "../components/book/BookCard/BookCard.vue";
import BookCoverTile from "../components/book/BookCoverTile.vue";
import BookContextMenu from "../components/book/BookContextMenu.vue";
import BookSearchModal from "../components/modals/BookSearchModal.vue";
import BooksSearchHeader from "../components/ui/BooksSearchHeader.vue";
import LibraryNav from "../components/ui/LibraryNav.vue";
import NavigationBar from "../components/ui/NavigationBar.vue";
import { ReadingStatus, type PaginatedBooks, type Book, type BookList } from "../api/types";
import { useCachedQuery } from "../composables/useCachedQuery";
import { useAddBook } from "../composables/useAddBook";
import { cacheKeys } from "../cache/keys";

const currentPage = ref(1);
const pageSize = ref(30);
const router = useRouter();
const accumulatedBooks = ref<Book[]>([]);
const isLoadingMore = ref(false);

const searchQuery = ref("");
const shelfFilter = ref<"to-read" | "finished">("to-read");
const activeListId = ref<number | null>(null);

const { data: listsData } = useCachedQuery<BookList[]>(cacheKeys.lists(), () => getLists());

const lists = computed(() => listsData.value ?? []);

watch(
  lists,
  (newLists) => {
    if (newLists.length && !activeListId.value) {
      setActiveListForShelf();
    }
  },
  { immediate: true },
);

const {
  data: booksData,
  error: booksError,
  refresh: refreshBooks,
} = useCachedQuery<PaginatedBooks>(
  computed(() =>
    activeListId.value ? cacheKeys.listBooks(activeListId.value, currentPage.value, pageSize.value) : "",
  ),
  () => getListBooks(activeListId.value!, currentPage.value, pageSize.value),
  { enabled: computed(() => activeListId.value !== null) },
);

const error = computed(() => {
  const e = booksError.value;
  if (!e) return "";
  if (e instanceof Error) return e.message;
  return "Failed to load books. Please try again.";
});

// Load saved view mode from localStorage, default to 'list'
const savedViewMode = localStorage.getItem("booksViewMode") as "list" | "grid" | null;
const viewMode = ref<"list" | "grid">(savedViewMode || "list");

// Watch viewMode and save to localStorage whenever it changes
watch(viewMode, (newMode) => {
  localStorage.setItem("booksViewMode", newMode);
});

watch(booksData, (next) => {
  if (!next) return;
  if (next.page === 1) {
    accumulatedBooks.value = [...next.items];
  } else {
    const seen = new Set(accumulatedBooks.value.map((b) => b.id));
    const additions = next.items.filter((b) => !seen.has(b.id));
    accumulatedBooks.value = [...accumulatedBooks.value, ...additions];
  }
  isLoadingMore.value = false;
  nextTick(() => {
    if (sentinelObserver && sentinelEl.value) {
      sentinelObserver.unobserve(sentinelEl.value);
      sentinelObserver.observe(sentinelEl.value);
    }
  });
});

const hasMore = computed(() => Boolean(booksData.value) && currentPage.value < (booksData.value?.pages ?? 1));

const filteredBooks = computed(() => {
  if (!booksData.value && accumulatedBooks.value.length === 0) return [];

  let books = accumulatedBooks.value;

  // Filter by search query
  if (searchQuery.value.trim()) {
    const query = searchQuery.value.toLowerCase().trim();
    books = books.filter(
      (book) => book.title.toLowerCase().includes(query) || book.author.toLowerCase().includes(query),
    );
  }

  return books;
});

const currentlyReadingBooks = computed(() =>
  filteredBooks.value.filter((book) => book.user_status?.status === ReadingStatus.STARTED),
);
const toReadBooks = computed(() =>
  filteredBooks.value.filter((book) => book.user_status?.status !== ReadingStatus.STARTED),
);

const gridBooks = ref<Book[]>([]);
const gridCurrentlyReading = ref<Book[]>([]);
const gridToRead = ref<Book[]>([]);
const isDragging = ref(false);
const lastDragTime = ref(0);
watch(
  filteredBooks,
  (next) => {
    gridBooks.value = [...next];
    gridCurrentlyReading.value = next.filter((book) => book.user_status?.status === ReadingStatus.STARTED);
    gridToRead.value = next.filter((book) => book.user_status?.status !== ReadingStatus.STARTED);
  },
  { immediate: true },
);

function getShelfListName(): string {
  return shelfFilter.value === "to-read" ? "To Read" : "Finished";
}

function setActiveListForShelf() {
  const targetName = getShelfListName();
  const match = lists.value.find((list) => list.name === targetName) || null;
  activeListId.value = match ? match.id : null;
}

async function loadBooks() {
  await refreshBooks();
}

function resetPagination() {
  currentPage.value = 1;
  accumulatedBooks.value = [];
}

async function loadMore() {
  if (isLoadingMore.value || !hasMore.value) return;
  isLoadingMore.value = true;
  currentPage.value += 1;
}

let sentinelObserver: IntersectionObserver | null = null;
const sentinelEl = ref<HTMLElement | null>(null);

function setupObserver() {
  if (sentinelObserver || !sentinelEl.value) return;
  sentinelObserver = new IntersectionObserver(
    (entries) => {
      for (const entry of entries) {
        if (entry.isIntersecting) loadMore();
      }
    },
    { rootMargin: "400px 0px" },
  );
  sentinelObserver.observe(sentinelEl.value);
}

watch(sentinelEl, () => {
  if (sentinelObserver) {
    sentinelObserver.disconnect();
    sentinelObserver = null;
  }
  nextTick(() => setupObserver());
});

onMounted(() => nextTick(() => setupObserver()));
onBeforeUnmount(() => {
  sentinelObserver?.disconnect();
  sentinelObserver = null;
});

const { showSearchModal, openSearch, closeSearch, selectBook } = useAddBook(async () => {
  resetPagination();
  await refreshBooks();
});

// Switching surfaces (To Read / Finished) loads the matching list from scratch.
watch(shelfFilter, () => {
  resetPagination();
  setActiveListForShelf();
  loadBooks();
});

function handleDragStart() {
  isDragging.value = true;
  // Starting a drag dismisses any open long-press menu, revealing the book being
  // moved (the drag was already armed underneath the menu).
  closeContextMenu();
}

async function handleDragEndForList(list: Book[], event: { newIndex?: number; oldIndex?: number } | null) {
  isDragging.value = false;
  lastDragTime.value = Date.now();

  if (!event || event.newIndex === undefined || event.oldIndex === undefined) {
    return;
  }
  if (event.newIndex === event.oldIndex) {
    return;
  }
  if (!activeListId.value) {
    return;
  }
  if (searchQuery.value.trim()) {
    return;
  }

  const movedBook = list[event.newIndex];
  if (!movedBook) return;
  const beforeBook = event.newIndex > 0 ? list[event.newIndex - 1] : null;
  const afterBook = event.newIndex < list.length - 1 ? list[event.newIndex + 1] : null;

  try {
    await reorderListItem(activeListId.value, {
      moved_book_id: movedBook.id,
      before_book_id: beforeBook?.id ?? null,
      after_book_id: afterBook?.id ?? null,
    });
    accumulatedBooks.value =
      shelfFilter.value === "to-read" ? [...gridCurrentlyReading.value, ...gridToRead.value] : [...gridBooks.value];
  } catch (err: any) {
    console.error("Failed to reorder books:", err);
  }
}

function handleCoverClick(bookId: number) {
  if (isDragging.value) return;
  if (Date.now() - lastDragTime.value < 200) return;
  router.push({ name: "book-detail", params: { id: bookId } });
}

const contextMenu = ref<{ visible: boolean; x: number; y: number; bookId: number | null }>({
  visible: false,
  x: 0,
  y: 0,
  bookId: null,
});

function openContextMenu(payload: { bookId: number; x: number; y: number }) {
  contextMenu.value = { visible: true, x: payload.x, y: payload.y, bookId: payload.bookId };
}

function closeContextMenu() {
  contextMenu.value.visible = false;
  contextMenu.value.bookId = null;
}

function handleContextView() {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();
  if (bookId !== null) router.push({ name: "book-detail", params: { id: bookId } });
}

const dragOpts = computed(() => ({
  "item-key": "id",
  animation: 150,
  delay: 120,
  "delay-on-touch-only": true,
  disabled: Boolean(searchQuery.value.trim()),
  "ghost-class": "grid-ghost",
  "drag-class": "grid-drag",
  "chosen-class": "grid-chosen",
}));
</script>

<template>
  <div class="books-view">
    <NavigationBar @add-book="openSearch">
      <template #nav>
        <LibraryNav v-model="shelfFilter" />
      </template>
    </NavigationBar>

    <div class="container">
      <div v-if="error" class="error">
        {{ error }}
      </div>

      <BooksSearchHeader v-model:search-query="searchQuery" v-model:view-mode="viewMode" />

      <div v-if="booksData && filteredBooks.length === 0" class="empty-state">
        <p v-if="searchQuery">No books match your search.</p>
        <p v-else-if="shelfFilter === 'finished'">No finished books yet.</p>
        <p v-else>No books yet. Add your first book to get started!</p>
      </div>

      <template v-if="viewMode === 'grid'">
        <template v-if="shelfFilter === 'to-read'">
          <section v-if="gridCurrentlyReading.length" class="shelf-section">
            <h2 class="shelf-section-title">Reading now</h2>
            <draggable
              class="books-container books-grid sectioned"
              :list="gridCurrentlyReading"
              v-bind="dragOpts"
              @start="handleDragStart"
              @end="handleDragEndForList(gridCurrentlyReading, $event)"
            >
              <template #item="{ element: book }">
                <BookCoverTile :book="book" show-progress @click="handleCoverClick" @menu="openContextMenu" />
              </template>
            </draggable>
          </section>

          <section v-if="gridToRead.length" class="shelf-section">
            <h2 class="shelf-section-title">Want to read</h2>
            <draggable
              class="books-container books-grid sectioned"
              :list="gridToRead"
              v-bind="dragOpts"
              @start="handleDragStart"
              @end="handleDragEndForList(gridToRead, $event)"
            >
              <template #item="{ element: book }">
                <BookCoverTile :book="book" @click="handleCoverClick" @menu="openContextMenu" />
              </template>
            </draggable>
          </section>
        </template>

        <draggable
          v-else
          class="books-container books-grid"
          :list="gridBooks"
          v-bind="dragOpts"
          @start="handleDragStart"
          @end="handleDragEndForList(gridBooks, $event)"
        >
          <template #item="{ element: book }">
            <BookCoverTile :book="book" @click="handleCoverClick" @menu="openContextMenu" />
          </template>
        </draggable>
      </template>

      <div v-else class="books-container books-list">
        <template v-if="shelfFilter === 'to-read'">
          <section v-if="currentlyReadingBooks.length" class="shelf-section">
            <h2 class="shelf-section-title">Reading now</h2>
            <div v-for="book in currentlyReadingBooks" :key="book.id">
              <BookCard :book="book" @menu="openContextMenu" />
            </div>
          </section>
          <section v-if="toReadBooks.length" class="shelf-section">
            <h2 class="shelf-section-title">Want to read</h2>
            <div v-for="book in toReadBooks" :key="book.id">
              <BookCard :book="book" @menu="openContextMenu" />
            </div>
          </section>
        </template>
        <div v-else v-for="book in filteredBooks" :key="book.id">
          <BookCard :book="book" @menu="openContextMenu" />
        </div>
      </div>

      <div v-if="hasMore || isLoadingMore" ref="sentinelEl" class="infinite-sentinel">
        <span v-if="isLoadingMore" class="infinite-loading">Loading more…</span>
      </div>
    </div>

    <BookSearchModal v-if="showSearchModal" @close="closeSearch" @select="selectBook" />

    <BookContextMenu
      v-if="contextMenu.visible && contextMenu.bookId !== null"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @view="handleContextView"
      @close="closeContextMenu"
    />
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
  gap: 1.25rem;
  align-items: center;
  width: 100%;
  max-width: 100%;
  padding-top: 6px;
  padding-bottom: var(--spacing-sm);
  overflow-x: clip;
  overflow-y: visible;
}

/*noinspection CssUnusedSymbol*/
.books-grid :deep(.sortable-ghost .grid-cover),
.books-grid :deep(.sortable-ghost .grid-cover-placeholder),
.books-grid :deep(.sortable-chosen .grid-cover),
.books-grid :deep(.sortable-chosen .grid-cover-placeholder),
.books-grid :deep(.sortable-drag .grid-cover),
.books-grid :deep(.sortable-drag .grid-cover-placeholder) {
  transform: none;
  box-shadow: var(--shadow);
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
  .books-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 1.25rem;
  }
}

@media (max-width: 480px) {
  .books-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
  }
}

/* Desktop: LibraryNav is inline tabs, not a fixed bar — drop the reserved space. */
@media (min-width: 769px) {
  .books-view {
    padding-bottom: var(--spacing-xl);
  }
}

/* vuedraggable applies these classes at runtime to slot content during drag. */
/*noinspection CssUnusedSymbol*/
.grid-ghost {
  opacity: 0;
}

/*noinspection CssUnusedSymbol*/
.grid-drag,
.grid-chosen {
  opacity: 1 !important;
}
</style>
