<script setup lang="ts">
import { computed, nextTick, ref, type Ref, watch } from "vue";
import { useRouter } from "vue-router";
import draggable from "vuedraggable";
import BookCard from "./BookCard/BookCard.vue";
import BookContextMenu from "./BookContextMenu.vue";
import BookCoverTile from "./BookCoverTile.vue";
import ShelfViewModeToggle from "./ShelfViewModeToggle.vue";
import { getShelfBooks } from "../../api/books";
import type { Book, ShelfName } from "../../api/types";
import { cacheKeys } from "../../cache/keys";
import { useContextMenu } from "../../composables/useContextMenu";
import { useInfiniteScroll } from "../../composables/useInfiniteScroll";
import { useLibraryPage } from "../../composables/useLibraryPage";
import { usePaginatedList } from "../../composables/usePaginatedList";
import { useShelfReorder } from "../../composables/useShelfReorder";
import { useShelfViewMode, type ViewMode } from "../../composables/useShelfViewMode";

const props = withDefaults(
  defineProps<{
    shelf: ShelfName;
    /** Heading above the shelf. Omitted when the page shows a single, self-evident shelf. */
    title?: string | null;
    showProgress?: boolean;
    /** Whether to page in more books as the shelf's end scrolls into view. */
    paginated?: boolean;
    pageSize?: number;
    /** Layout this shelf starts in, until the reader picks one; theirs is then remembered. */
    defaultViewMode?: ViewMode;
  }>(),
  { title: null, showProgress: false, paginated: false, pageSize: 30, defaultViewMode: "list" },
);

const router = useRouter();
const { searchQuery, shelves, refreshToken, registerShelf } = useLibraryPage();

// Deliberately this shelf's own, not the page's: shelves on one page can be laid out differently.
const viewMode = useShelfViewMode(props.shelf, props.defaultViewMode);

const shelfId = computed(() => shelves.value.find((shelf) => shelf.name === props.shelf)?.id ?? null);

const {
  items,
  replaceItems,
  hasMore,
  isLoadingMore,
  loaded,
  error: loadError,
  loadMore,
  reload,
} = usePaginatedList<Book>({
  resourceId: shelfId,
  cacheKey: (id, page) => cacheKeys.shelfBooks(id, page, props.pageSize),
  cacheKeyPrefix: (id) => cacheKeys.shelfBooksPrefix(id),
  fetchPage: (id, page) => getShelfBooks(id, page, props.pageSize),
  itemKey: (book) => book.id,
});

// The page reloads its shelves after mutating the library (e.g. adding a book)
watch(refreshToken, () => void reload());

const error = computed(() => {
  const e = loadError.value;
  if (!e) return "";
  if (e instanceof Error) return e.message;
  return "Failed to load books. Please try again.";
});

const filteredBooks = computed(() => {
  const query = searchQuery.value.toLowerCase().trim();
  if (!query) return items.value;

  return items.value.filter(
    (book) => book.title.toLowerCase().includes(query) || book.author.toLowerCase().includes(query),
  );
});

/**
 * vuedraggable reorders the array it renders from in place, so the shelf draws from a mutable
 * copy that re-syncs whenever the filtered list changes.
 */
const books = ref<Book[]>([]) as Ref<Book[]>;

watch(
  filteredBooks,
  (next) => {
    books.value = [...next];
  },
  { immediate: true },
);

registerShelf(computed(() => ({ loaded: loaded.value, count: filteredBooks.value.length })));

// Reordering persists positions against the shelf, which only makes sense while the full shelf is
// on screen (i.e., no search filter is active)
const isReorderable = computed(() => !searchQuery.value.trim());

const { dragOptions, ignoresClick, handleDragStart, handleDragEnd, moveBookToEdge } = useShelfReorder({
  books,
  shelfId,
  enabled: isReorderable,
  onPersisted: replaceItems,
});

const showSentinel = computed(() => props.paginated && (hasMore.value || isLoadingMore.value));

const sentinelEl = ref<HTMLElement | null>(null);
const { reobserve } = useInfiniteScroll(sentinelEl, loadMore);

// Re-observe once a fresh page has rendered, so the sentinel keeps triggering.
watch(items, () => void nextTick(reobserve));

const { contextMenu, openContextMenu, closeContextMenu } = useContextMenu();

function startDrag() {
  // Starting a drag dismisses any open long-press menu, revealing the book being
  // moved (the drag was already armed underneath the menu).
  closeContextMenu();
  handleDragStart();
}

function handleCoverClick(bookId: number) {
  if (ignoresClick()) return;
  router.push({ name: "book-detail", params: { id: bookId } });
}

function handleContextView() {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();
  if (bookId !== null) router.push({ name: "book-detail", params: { id: bookId } });
}

function handleContextMove(edge: "top" | "bottom") {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();
  if (bookId !== null) void moveBookToEdge(bookId, edge);
}
</script>

<template>
  <!-- Nothing to show at all (an empty shelf, still loading) leaves no box behind, so the page's
       spacing between shelves never has to account for invisible ones. -->
  <section v-if="books.length || error || showSentinel" class="book-shelf">
    <div v-if="error" class="error">
      {{ error }}
    </div>

    <template v-if="books.length">
      <!-- Titleless shelves still get the shelf header row, so their toggle stays where a titled shelf's would be. -->
      <header class="book-shelf-header">
        <h2 v-if="title" class="book-shelf-title">{{ title }}</h2>
        <ShelfViewModeToggle v-model="viewMode" />
      </header>

      <draggable
        v-if="viewMode === 'grid'"
        class="books-container books-grid"
        :list="books"
        item-key="id"
        :disabled="!isReorderable"
        v-bind="dragOptions"
        @start="startDrag"
        @end="handleDragEnd"
      >
        <template #item="{ element: book }">
          <BookCoverTile :book="book" :show-progress="showProgress" @click="handleCoverClick" @menu="openContextMenu" />
        </template>
      </draggable>

      <div v-else class="books-container books-list">
        <div v-for="book in books" :key="book.id">
          <BookCard :book="book" @menu="openContextMenu" />
        </div>
      </div>
    </template>

    <div v-if="showSentinel" ref="sentinelEl" class="infinite-sentinel">
      <span v-if="isLoadingMore" class="infinite-loading">Loading more…</span>
    </div>

    <BookContextMenu
      v-if="contextMenu.visible && contextMenu.bookId !== null"
      :x="contextMenu.x"
      :y="contextMenu.y"
      @view="handleContextView"
      @move="handleContextMove"
      @close="closeContextMenu"
    />
  </section>
</template>

<style scoped>
.book-shelf-header {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-height: 30px;
  margin-bottom: var(--spacing-sm);
}

.book-shelf-header > :last-child {
  margin-left: auto;
}

.book-shelf-title {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.books-container {
  overflow-x: clip;
  overflow-y: visible;
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
</style>
