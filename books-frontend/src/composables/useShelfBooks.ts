import { useInfiniteQuery } from "@tanstack/vue-query";
import { computed, ref, type Ref, watch } from "vue";
import { getShelfBooks } from "../api/books";
import type { Book, ShelfRef } from "../api/types";
import { queryKeys } from "../query/keys";
import { useLibraryPage } from "./useLibraryPage.ts";
import { useShelfOrder } from "./useShelfOrder";

export interface ShelfBooksOptions {
  shelf: ShelfRef;
  pageSize: number;
}

export function useShelfBooks(options: ShelfBooksOptions) {
  const { searchQuery, registerShelf } = useLibraryPage();

  const {
    data,
    error: loadError,
    hasNextPage: hasMore,
    isFetching,
    isPending,
    fetchNextPage,
    refetch,
  } = useInfiniteQuery({
    queryKey: computed(() => queryKeys.shelves.books(options.shelf, options.pageSize)),
    queryFn: ({ pageParam }) => getShelfBooks(options.shelf, pageParam, options.pageSize),
    initialPageParam: 1,
    getNextPageParam: (last) => (last.page < last.pages ? last.page + 1 : undefined),
  });

  /** True once the first page has resolved at least once. */
  const loaded = computed(() => data.value !== undefined);

  /** True while a further page loads or the loaded pages refresh, but not during the very first load. */
  const isLoadingMore = computed(() => isFetching.value && !isPending.value);

  const items = computed(() => {
    // A book that moved between two pages while they were fetched shows once
    const unique = new Map<number, Book>();
    for (const page of data.value?.pages ?? []) {
      for (const book of page.items) {
        if (!unique.has(book.id)) {
          unique.set(book.id, book);
        }
      }
    }

    return [...unique.values()];
  });

  function loadMore() {
    if (!isFetching.value && hasMore.value) {
      void fetchNextPage();
    }
  }

  /**
   * Refetches every loaded page, keeping the books visible meanwhile, then shows the server's order again. Rejects when
   * that fails.
   */
  async function refresh() {
    await refetch({ throwOnError: true });
    // The watcher below doesn't run when the refetch changed nothing, e.g. when the server rejected a move
    books.value = [...filteredBooks.value];
  }

  const error = computed(() => {
    const e = loadError.value;

    if (!e) {
      return "";
    }

    if (e instanceof Error) {
      return e.message;
    }

    return "Failed to load books. Please try again.";
  });

  const query = computed(() => searchQuery.value.toLowerCase().trim());

  const isFiltered = computed(() => query.value !== "");

  const filteredBooks = computed(() => {
    if (!isFiltered.value) {
      return items.value;
    }

    return items.value.filter(
      (book) =>
        book.title.toLowerCase().includes(query.value) || (book.author ?? "").toLowerCase().includes(query.value),
    );
  });

  /**
   * The shelf's books as shown: a copy of the loaded books that a move changes right away, before it is saved. Dragging
   * a book reorders this very array.
   */
  const books = ref<Book[]>([]) as Ref<Book[]>;

  watch(
    filteredBooks,
    (next) => {
      books.value = [...next];
    },
    { immediate: true },
  );

  const { isSaving, canReorder, saveBookAt, moveBookToEdge } = useShelfOrder({
    books,
    hasMore,
    shelf: options.shelf,
    isFiltered,
    isLoadingMore,
    hasError: computed(() => !!error.value),
    refresh,
  });

  registerShelf(computed(() => ({ loaded: loaded.value, count: filteredBooks.value.length })));

  return { books, error, hasMore, isLoadingMore, loadMore, isSaving, canReorder, saveBookAt, moveBookToEdge };
}
