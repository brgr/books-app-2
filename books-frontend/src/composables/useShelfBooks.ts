import { computed, watch } from "vue";
import { getShelfBooks } from "../api/books";
import type { Book, ShelfName } from "../api/types";
import { cacheKeys } from "../cache/keys";
import { useLibraryPage } from "./useLibraryPage.ts";
import { usePaginatedList } from "./usePaginatedList.ts";
import { useShelves } from "./useShelves.ts";

export interface ShelfBooksOptions {
  shelf: ShelfName;
  pageSize: number;
}

export function useShelfBooks(options: ShelfBooksOptions) {
  const { searchQuery, refreshToken, registerShelf } = useLibraryPage();
  const { shelves } = useShelves();

  const shelfId = computed(() => shelves.value.find((shelf) => shelf.name === options.shelf)?.id ?? null);

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
    cacheKey: (id, page) => cacheKeys.shelfBooks(id, page, options.pageSize),
    cacheKeyPrefix: (id) => cacheKeys.shelfBooksPrefix(id),
    fetchPage: (id, page) => getShelfBooks(id, page, options.pageSize),
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

  const books = computed(() => {
    const query = searchQuery.value.toLowerCase().trim();
    if (!query) return items.value;

    return items.value.filter(
      (book) => book.title.toLowerCase().includes(query) || book.author.toLowerCase().includes(query),
    );
  });

  registerShelf(computed(() => ({ loaded: loaded.value, count: books.value.length })));

  return { books, shelfId, error, hasMore, isLoadingMore, loadMore, replaceItems };
}
