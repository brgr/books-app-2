<script setup lang="ts">
import { computed, nextTick, ref, type Ref, watch } from "vue";
import { useRouter } from "vue-router";
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
import { useShelfReorder } from "../../composables/useShelfReorder";
import { useShelfViewMode, type ViewMode } from "../../composables/useShelfViewMode";
import { removeBookFromShelf } from "../../api/books";
import { invalidateCache } from "../../cache/invalidate";

const props = withDefaults(
  defineProps<{
    shelf: ShelfRef;
    /** Heading above the shelf. Omitted when the page shows a single, self-evident shelf. */
    title?: string | null;
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
const { searchQuery } = useLibraryPage();

// Deliberately this shelf's own, not the page's: shelves on one page can be laid out differently.
const viewMode = useShelfViewMode(props.shelf, props.defaultViewMode);

const { books: filteredBooks, error, hasMore, isLoadingMore, loadMore, reload, refreshLoaded } = useShelfBooks(props);

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

const {
  isDragging,
  isSaving,
  message,
  error: reorderError,
  dragOptions,
  ignoresClick,
  handleDragStart,
  handleDragEnd,
  moveBookToEdge,
} = useShelfReorder({
  books,
  hasMore,
  shelf: props.shelf,
  enabled: isReorderable,
  refresh: refreshLoaded,
});

const showSentinel = computed(() => props.paginated && (hasMore.value || isLoadingMore.value));

const sentinelEl = ref<HTMLElement | null>(null);
const { reobserve } = useInfiniteScroll(
  sentinelEl,
  () => {
    if (!isDragging.value && !isSaving.value && !error.value) {
      loadMore();
    }
  },
  "1200px 0px",
);
watch([isDragging, isSaving], () => void nextTick(reobserve));

// Re-observe once a fresh page has rendered, so the sentinel keeps triggering.
watch(filteredBooks, () => void nextTick(reobserve));

const { contextMenu, openContextMenu, closeContextMenu } = useContextMenu();

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

  router.push({ name: "book-detail", params: { id: bookId } });
}

function handleContextView() {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();

  if (bookId !== null) {
    router.push({ name: "book-detail", params: { id: bookId } });
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
    await invalidateCache.shelfChanged(bookId);
    await reload();
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
    <p v-if="reorderError" role="alert" class="error">{{ reorderError }}</p>
    <p v-if="message" role="status">{{ message }}</p>

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
        :disabled="!isReorderable || isSaving"
        v-bind="dragOptions"
        @start="startDrag"
        @end="handleDragEnd"
      >
        <template #item="{ element: book }">
          <BookCoverTile
            :book="book"
            :href="router.resolve({ name: 'book-detail', params: { id: book.id } }).href"
            :show-progress="showProgress"
            @click="handleCoverClick"
            @menu="openContextMenu"
          />
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
      :can-remove-from-shelf="canRemoveFromShelf"
      :can-reorder="isReorderable && !isSaving"
      @view="handleContextView"
      @move="handleContextMove"
      @remove-from-shelf="handleContextRemove"
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
