<script setup lang="ts">
import { computed, nextTick, ref, type Ref, useId, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import draggable from "vuedraggable";
import BookCard from "./BookCard/BookCard.vue";
import BookContextMenu from "./BookContextMenu.vue";
import BookCoverTile from "./BookCoverTile.vue";
import ShelfViewModeToggle from "./ShelfViewModeToggle.vue";
import type { Book, ShelfRef } from "../../api/types";
import { useContextMenu } from "../../composables/useContextMenu";
import { useInfiniteScroll } from "../../composables/useInfiniteScroll";
import { useLibraryPage } from "../../composables/useLibraryPage";
import { useShelfBooks } from "../../composables/useShelfBooks";
import { useShelfDrag } from "../../composables/useShelfDrag";
import { useShelfOrder } from "../../composables/useShelfOrder";
import { useShelfViewMode, type ViewMode } from "../../composables/useShelfViewMode";
import { removeBookFromShelf } from "../../api/books";
import { invalidateAfter } from "../../query/invalidate";
import { useSeedBook } from "../../composables/useBook";

const props = withDefaults(
  defineProps<{
    shelf: ShelfRef;
    /** Heading above the shelf. Omitted when the page shows a single, self-evident shelf. */
    title?: string | null;
    /** Start folded until the reader expands the shelf; remember their choice on this device. */
    collapsible?: boolean;
    showProgress?: boolean;
    /** Whether to page in more books as the shelf's end scrolls into view. */
    paginated?: boolean;
    pageSize?: number;
    /** Layout this shelf starts in, until the reader picks one; theirs is then remembered. */
    defaultViewMode?: ViewMode;
    /** Whether this shelf supports removing a book without removing it from the library. */
    canRemoveFromShelf?: boolean;
  }>(),
  { title: null, showProgress: false, paginated: false, pageSize: 100, defaultViewMode: "list" },
);

const router = useRouter();
const seedBook = useSeedBook();
const route = useRoute();

function detailRoute(bookId: number) {
  return { name: "book-detail", params: { id: bookId }, query: { from: route.fullPath } };
}
const { searchQuery } = useLibraryPage();

// Deliberately this shelf's own, not the page's: shelves on one page can be laid out differently.
const viewMode = useShelfViewMode(props.shelf, props.defaultViewMode);

const contentId = useId();
const collapseStorageKey = `shelfCollapsed:${props.shelf}`;
const isCollapsed = ref(readCollapsed());

function readCollapsed(): boolean {
  if (!props.collapsible) {
    return false;
  }
  try {
    return localStorage.getItem(collapseStorageKey) !== "false";
  } catch {
    return true;
  }
}

function toggleCollapsed() {
  isCollapsed.value = !isCollapsed.value;
  closeContextMenu();
  try {
    localStorage.setItem(collapseStorageKey, String(isCollapsed.value));
  } catch {
    // The toggle still works when browser storage is unavailable.
  }
}

const { books: filteredBooks, error, hasMore, isLoadingMore, loadMore, refresh } = useShelfBooks(props);

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

// A filtered list hides potential neighbors, so it cannot be reordered.
// Reordering is also disabled while more books are loading, or if the shelf has an error.
const isReorderable = computed(() => !searchQuery.value.trim() && !isLoadingMore.value && !error.value);

const { contextMenu, openContextMenu, closeContextMenu } = useContextMenu();

const contextMenuBook = computed(() => books.value.find((book) => book.id === contextMenu.value.bookId) ?? null);

const { isSaving, canReorder, saveBookAt, moveBookToEdge } = useShelfOrder({
  books,
  hasMore,
  shelf: props.shelf,
  enabled: isReorderable,
  refresh: reconcileOrder,
});

const { isDragging, dragOptions, ignoresClick, handleChoose, handleDragStart, handleDragEnd } = useShelfDrag({
  books,
  canDrag: canReorder,
  onPickUp: (bookId, rect) => openContextMenu({ bookId, x: rect.left, y: rect.bottom, anchor: rect }),
  onDrop: (index) => void saveBookAt(index),
});

/**
 * Brings the shelf back in line with the server after a reorder. A refresh that finds the order unchanged (the
 * reorder was rejected) leaves `filteredBooks` as it was, so the dragged copy is reset here rather than by the watcher.
 */
async function reconcileOrder() {
  await refresh();
  books.value = [...filteredBooks.value];
}

const showSentinel = computed(() => props.paginated && (hasMore.value || isLoadingMore.value));

const sentinelEl = ref<HTMLElement | null>(null);
const { reobserve } = useInfiniteScroll(
  sentinelEl,
  () => {
    if (!isCollapsed.value && !isDragging.value && !isSaving.value && !error.value) {
      loadMore();
    }
  },
  "1200px 0px",
);
watch([isDragging, isSaving, isCollapsed], () => void nextTick(reobserve));

// The observer only fires when the sentinel enters or leaves the view, so we re-observe to check a sentinel that stayed in view:
// - after a new page renders, since the sentinel may still be in view
// - after any fetch ends, since loadMore skips while one runs, and a background refetch that changes nothing renders nothing
watch([filteredBooks, isLoadingMore], () => void nextTick(reobserve));

function startDrag() {
  // Starting a drag dismisses any open long-press menu, revealing the book being
  // moved (the drag was already armed underneath the menu).
  closeContextMenu();
  handleDragStart();
}

function handleCoverClick(bookId: number) {
  if (ignoresClick()) {
    return;
  }

  openBook(bookId);
}

function openBook(bookId: number) {
  const book = books.value.find((book) => book.id === bookId);
  if (book) {
    seedBook(book);
    void router.push(detailRoute(bookId));
  }
}

function handleContextView() {
  // The lifted book sits right under the finger that picked it up: lifting that finger must not view it
  if (ignoresClick()) {
    return;
  }

  const bookId = contextMenu.value.bookId;
  closeContextMenu();

  if (bookId !== null) {
    openBook(bookId);
  }
}

function handleContextMove(edge: "top" | "bottom") {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();

  if (bookId !== null) {
    void moveBookToEdge(bookId, edge);
  }
}

async function handleContextRemove() {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();

  if (bookId === null || !props.canRemoveFromShelf) {
    return;
  }

  try {
    await removeBookFromShelf(props.shelf, bookId);
    invalidateAfter.shelfChanged(bookId);
  } catch (error) {
    console.error("Failed to remove book from shelf:", error);
    alert("Failed to remove book from this shelf.");
  }
}
</script>

<template>
  <!-- Nothing to show at all (an empty shelf, still loading) leaves no box behind, so the page's
       spacing between shelves never has to account for invisible ones. -->
  <section v-if="books.length || error || showSentinel" class="book-shelf">
    <div v-if="error" class="error">
      {{ error }}
    </div>

    <!-- Titleless shelves still get the shelf header row, so their toggle stays where a titled shelf's would be. -->
    <header v-if="books.length" class="book-shelf-header">
      <h2 v-if="title" class="book-shelf-title">
        <button
          v-if="collapsible"
          type="button"
          class="shelf-collapse-toggle"
          :aria-expanded="!isCollapsed"
          :aria-controls="contentId"
          @click="toggleCollapsed"
        >
          {{ title }}
          <svg
            class="shelf-chevron"
            :class="{ expanded: !isCollapsed }"
            width="16"
            height="16"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            aria-hidden="true"
          >
            <path d="m9 5 7 7-7 7" />
          </svg>
        </button>
        <template v-else>{{ title }}</template>
      </h2>
      <ShelfViewModeToggle v-if="!isCollapsed" v-model="viewMode" class="shelf-view-toggle" />
    </header>

    <div v-show="!isCollapsed" :id="contentId">
      <draggable
        v-if="books.length && viewMode === 'grid'"
        class="books-container books-grid"
        :list="books"
        item-key="id"
        v-bind="dragOptions"
        @choose="handleChoose"
        @start="startDrag"
        @end="handleDragEnd"
      >
        <template #item="{ element: book }">
          <BookCoverTile
            :book="book"
            :href="router.resolve(detailRoute(book.id)).href"
            :show-progress="showProgress"
            @click="handleCoverClick"
            @menu="openContextMenu"
          />
        </template>
      </draggable>

      <div v-else-if="books.length" class="books-container books-list">
        <div v-for="book in books" :key="book.id">
          <BookCard :book="book" @menu="openContextMenu" />
        </div>
      </div>

      <div v-if="showSentinel" ref="sentinelEl" class="infinite-sentinel">
        <span v-if="isLoadingMore" class="infinite-loading">Loading more…</span>
      </div>
    </div>

    <BookContextMenu
      v-if="contextMenu.bookId !== null"
      :x="contextMenu.x"
      :y="contextMenu.y"
      :anchor="contextMenu.anchor"
      :can-remove-from-shelf="canRemoveFromShelf"
      :can-reorder="canReorder"
      @view="handleContextView"
      @move="handleContextMove"
      @remove-from-shelf="handleContextRemove"
      @close="closeContextMenu"
    >
      <template v-if="contextMenuBook" #preview>
        <BookCoverTile
          :book="contextMenuBook"
          :href="router.resolve(detailRoute(contextMenuBook.id)).href"
          :show-progress="showProgress"
        />
      </template>
    </BookContextMenu>
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

.shelf-view-toggle {
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

.shelf-collapse-toggle {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) 0;
  border: none;
  background: transparent;
  font: inherit;
  letter-spacing: inherit;
  text-transform: inherit;
  text-align: left;
}

.shelf-collapse-toggle:hover {
  background: transparent;
  color: var(--color-primary);
}

.shelf-collapse-toggle:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}

.shelf-chevron {
  flex-shrink: 0;
}

.shelf-chevron.expanded {
  transform: rotate(90deg);
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
  grid-template-columns: repeat(auto-fill, 120px);
  gap: 1.25rem;
  align-items: center;
  width: 100%;
  max-width: 100%;
  padding-top: 6px;
  padding-bottom: var(--spacing-sm);
  /* Make sure that covers on the left and right edge, when hovered, have their shadows visible */
  overflow: visible;
}

@media (max-width: 480px) {
  .books-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
  }
}

/* The book's place in the grid while it is dragged: where it will drop */
/* vuedraggable applies these classes at runtime to slot content during drag. */
/*noinspection CssUnusedSymbol*/
.grid-ghost {
  opacity: 0.2;
}

/* The copy following the finger or pointer (SortableJS makes it translucent inline) */
/*noinspection CssUnusedSymbol*/
.grid-drag {
  opacity: 1 !important;
}

/*noinspection CssUnusedSymbol*/
.books-grid :deep(.grid-drag .grid-cover),
.books-grid :deep(.grid-drag .grid-cover-placeholder) {
  transform: scale(1.06);
  box-shadow: 0 18px 40px rgba(0, 0, 0, 0.35);
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
