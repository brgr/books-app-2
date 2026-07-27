<script setup lang="ts">
import { computed, type MaybeRefOrGetter, nextTick, ref, type Ref, toValue, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getShelfBooks, getShelves, reorderShelfItem } from "../api/books";
import BookShelf from "../components/book/BookShelf.vue";
import BookContextMenu from "../components/book/BookContextMenu.vue";
import BookSearchModal from "../components/modals/BookSearchModal.vue";
import BooksSearchHeader from "../components/ui/BooksSearchHeader.vue";
import LibraryNav from "../components/ui/LibraryNav.vue";
import NavigationBar from "../components/ui/NavigationBar.vue";
import { type Book, ShelfName, type Shelf } from "../api/types";
import { useCachedQuery } from "../composables/useCachedQuery";
import { usePaginatedList } from "../composables/usePaginatedList";
import { useAddBook } from "../composables/useAddBook";
import { useInfiniteScroll } from "../composables/useInfiniteScroll";
import { useContextMenu } from "../composables/useContextMenu";
import { cacheKeys } from "../cache/keys";

const pageSize = 30;
const route = useRoute();
const router = useRouter();

const searchQuery = ref("");
// The shelf lives in the URL: /shelves/:shelf drives it, while bare "/" implies "to-read".
const shelfFilter = computed<"to-read" | "finished">(() =>
  route.params.shelf === "finished" ? "finished" : "to-read",
);

function goToShelf(shelf: "to-read" | "finished") {
  router.push({ name: "shelf", params: { shelf } });
}

const activeShelfId = ref<number | null>(null);

const { data: shelvesData } = useCachedQuery<Shelf[]>(cacheKeys.shelves(), () => getShelves());

const shelves = computed(() => shelvesData.value ?? []);

watch(
  shelves,
  (newShelves) => {
    if (newShelves.length && !activeShelfId.value) {
      setActiveShelfForTab();
    }
  },
  { immediate: true },
);

const {
  items: books,
  replaceItems: replaceBooks,
  hasMore,
  isLoadingMore,
  loaded: booksLoaded,
  error: booksError,
  loadMore,
  reload: reloadBooks,
} = usePaginatedList<Book>({
  resourceId: activeShelfId,
  cacheKey: (shelfId, page) => cacheKeys.shelfBooks(shelfId, page, pageSize),
  cacheKeyPrefix: (shelfId) => cacheKeys.shelfBooksPrefix(shelfId),
  fetchPage: (shelfId, page) => getShelfBooks(shelfId, page, pageSize),
  itemKey: (book) => book.id,
});

// We only get one page here for "Reading Now" books, which is fine, as we get up to 100 books, and more likely
// the user has like 3 to 5 books max in progress.
// In the future, we should consider that this could potentially be more for some users, and we should implement
// this better in some way.
const startedShelfId = computed(() => shelves.value.find((shelf) => shelf.name === ShelfName.STARTED)?.id ?? null);

const { data: startedBooksData, setData: setStartedBooks } = useCachedQuery<Book[]>(
  computed(() => (startedShelfId.value ? cacheKeys.shelfBooks(startedShelfId.value, 1, 100) : "")),
  () => getShelfBooks(startedShelfId.value as number, 1, 100).then((result) => result.items),
);

const startedBooks = computed(() => startedBooksData.value ?? []);

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

function matchesSearch(book: Book): boolean {
  const query = searchQuery.value.toLowerCase().trim();
  if (!query) return true;

  return book.title.toLowerCase().includes(query) || book.author.toLowerCase().includes(query);
}

const filteredBooks = computed(() => books.value.filter(matchesSearch));
const currentlyReadingBooks = computed(() => startedBooks.value.filter(matchesSearch));

/**
 * vuedraggable reorders the array it renders from in place, so each shelf draws from a mutable
 * copy that re-syncs whenever the underlying filtered list changes.
 */
function draggableMirror(source: MaybeRefOrGetter<Book[]>): Ref<Book[]> {
  const mirror = ref<Book[]>([]) as Ref<Book[]>;

  watch(
    () => toValue(source),
    (next) => {
      mirror.value = [...next];
    },
    { immediate: true },
  );

  return mirror;
}

const startedMirror = draggableMirror(currentlyReadingBooks);
const shelfMirror = draggableMirror(filteredBooks);

/** A shelf as this page renders it: which shelf to reorder against, its heading, and its books. */
interface DisplayedShelf {
  key: string;
  id: number | null;
  title: string | null;
  books: Book[];
  showProgress: boolean;
}

const visibleShelves = computed<DisplayedShelf[]>(() => {
  let shelvesInToReadTab = [
    {
      key: "started",
      id: startedShelfId.value,
      title: "Reading now",
      books: startedMirror.value,
      showProgress: true,
    },
    {
      key: "want-to-read",
      id: activeShelfId.value,
      title: "Want to read",
      books: shelfMirror.value,
      showProgress: false,
    },
  ];

  let shelfInFinishedTab = [
    {
      key: "finished",
      id: activeShelfId.value,
      title: null,
      books: shelfMirror.value,
      showProgress: false,
    },
  ];

  const shelves: DisplayedShelf[] = shelfFilter.value === "to-read" ? shelvesInToReadTab : shelfInFinishedTab;

  return shelves.filter((shelf) => shelf.books.length > 0);
});

const isEmpty = computed(() => visibleShelves.value.length === 0);

// Reordering persists positions against a shelf, which only makes sense while the full shelf is
// on screen (i.e., no search filter is active)
const isReorderable = computed(() => !searchQuery.value.trim());

const isDragging = ref(false);
const lastDragTime = ref(0);

function setActiveShelfForTab() {
  const targetName = shelfFilter.value === "to-read" ? ShelfName.WANT_TO_READ : ShelfName.FINISHED;
  const match = shelves.value.find((shelf) => shelf.name === targetName) || null;
  activeShelfId.value = match ? match.id : null;
}

const sentinelEl = ref<HTMLElement | null>(null);
const { reobserve } = useInfiniteScroll(sentinelEl, loadMore);

// Re-observe once a fresh page has rendered, so the sentinel keeps triggering.
watch(books, () => void nextTick(reobserve));

const { showSearchModal, openSearch, closeSearch, selectBook } = useAddBook(reloadBooks);

// Switching surfaces (To Read / Finished) points usePaginatedList at the matching list;
// it resets and reloads on its own from the resource change.
watch(shelfFilter, setActiveShelfForTab);

function handleDragStart() {
  isDragging.value = true;
  // Starting a drag dismisses any open long-press menu, revealing the book being
  // moved (the drag was already armed underneath the menu).
  closeContextMenu();
}

// Persists a reorder against the given shelf, then mirrors the new order back into whichever
// accumulator backs that shelf so it survives future page loads
async function commitReorder(
  shelfId: number,
  order: Book[],
  movedId: number,
  beforeId: number | null,
  afterId: number | null,
) {
  try {
    await reorderShelfItem(shelfId, {
      moved_book_id: movedId,
      before_book_id: beforeId,
      after_book_id: afterId,
    });

    if (shelfId === startedShelfId.value) {
      // The started shelf is a single cache entry (one page of up to 100), so rewriting it with the new order is
      // safe and survives a remount from cache
      await setStartedBooks([...order]);
    } else if (shelfId === activeShelfId.value) {
      // The paginated shelf spans multiple cache entries; replaceBooks invalidates them so the remount refetches
      await replaceBooks([...order]);
    }
  } catch (err: any) {
    console.error("Failed to reorder books:", err);
  }
}

async function handleDragEnd(shelf: DisplayedShelf, event: { newIndex?: number; oldIndex?: number } | null) {
  isDragging.value = false;
  lastDragTime.value = Date.now();

  if (!event || event.newIndex === undefined || event.oldIndex === undefined) {
    return;
  }
  if (event.newIndex === event.oldIndex) {
    return;
  }
  if (shelf.id === null || !isReorderable.value) {
    return;
  }

  const list = shelf.books;
  const movedBook = list[event.newIndex];
  if (!movedBook) return;
  const beforeBook = event.newIndex > 0 ? list[event.newIndex - 1] : null;
  const afterBook = event.newIndex < list.length - 1 ? list[event.newIndex + 1] : null;

  await commitReorder(shelf.id, list, movedBook.id, beforeBook?.id ?? null, afterBook?.id ?? null);
}

function handleCoverClick(bookId: number) {
  if (isDragging.value) return;
  if (Date.now() - lastDragTime.value < 200) return;
  router.push({ name: "book-detail", params: { id: bookId } });
}

const { contextMenu, openContextMenu, closeContextMenu } = useContextMenu();

function handleContextView() {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();
  if (bookId !== null) router.push({ name: "book-detail", params: { id: bookId } });
}

async function moveBookToEdge(bookId: number, edge: "top" | "bottom") {
  if (!isReorderable.value) return;

  const shelf = visibleShelves.value.find((candidate) => candidate.books.some((book) => book.id === bookId));
  if (!shelf || shelf.id === null) return;

  const list = shelf.books;
  const idx = list.findIndex((book) => book.id === bookId);
  const targetIndex = edge === "top" ? 0 : list.length - 1;
  if (idx === -1 || idx === targetIndex) return;

  // Reordered in place: this array is the one the shelf renders (and vuedraggable mutates) directly
  const [moved] = list.splice(idx, 1);
  if (edge === "top") list.unshift(moved);
  else list.push(moved);

  const beforeBook = edge === "bottom" ? (list[list.length - 2] ?? null) : null;
  const afterBook = edge === "top" ? (list[1] ?? null) : null;

  await commitReorder(shelf.id, list, moved.id, beforeBook?.id ?? null, afterBook?.id ?? null);
}

function handleContextMove(edge: "top" | "bottom") {
  const bookId = contextMenu.value.bookId;
  closeContextMenu();
  if (bookId !== null) moveBookToEdge(bookId, edge);
}
</script>

<template>
  <div class="books-view">
    <NavigationBar @add-book="openSearch">
      <template #nav>
        <LibraryNav :model-value="shelfFilter" @update:model-value="goToShelf" />
      </template>
    </NavigationBar>

    <div class="container">
      <div v-if="error" class="error">
        {{ error }}
      </div>

      <BooksSearchHeader v-model:search-query="searchQuery" v-model:view-mode="viewMode" />

      <div v-if="booksLoaded && isEmpty" class="empty-state">
        <p v-if="searchQuery">No books match your search.</p>
        <p v-else-if="shelfFilter === 'finished'">No finished books yet.</p>
        <p v-else>No books yet. Add your first book to get started!</p>
      </div>

      <div v-if="visibleShelves.length" class="shelves">
        <BookShelf
          v-for="shelf in visibleShelves"
          :key="shelf.key"
          :title="shelf.title"
          :books="shelf.books"
          :view-mode="viewMode"
          :show-progress="shelf.showProgress"
          :reorderable="isReorderable"
          @dragstart="handleDragStart"
          @dragend="handleDragEnd(shelf, $event)"
          @select="handleCoverClick"
          @menu="openContextMenu"
        />
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
      @move="handleContextMove"
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

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

.shelves {
  margin-top: var(--spacing-lg);
}

.shelves > * + * {
  margin-top: var(--spacing-lg);
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

/* Desktop: LibraryNav is inline tabs, not a fixed bar: drop the reserved space. */
@media (min-width: 769px) {
  .books-view {
    padding-bottom: var(--spacing-xl);
  }
}
</style>
