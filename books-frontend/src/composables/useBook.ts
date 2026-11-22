import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, type Ref } from "vue";
import { useRoute } from "vue-router";
import { getBook } from "../api/books";
import type { Book, ReadingState } from "../api/types";
import { queryKeys } from "../query/keys";

/** The book id in the current route's `id` parameter, or 0 when it isn't a number. */
export function useRouteBookId() {
  const route = useRoute();

  return computed(() => {
    const id = parseInt(route.params.id as string);
    return isNaN(id) ? 0 : id;
  });
}

export function useSeedBook() {
  const queryClient = useQueryClient();

  return (book: Book) => {
    const queryKey = queryKeys.book.detail(book.id);

    // Keep a book that is already cached, since it can be newer than the shelf's copy: a rating saved on the detail
    // page is in the cache at once, while the shelf only shows it after its next refetch.
    if (queryClient.getQueryData(queryKey) === undefined) {
      queryClient.setQueryData(queryKey, book);
    }
  };
}

/** Puts the reading state a mutation answered with into the cached book. */
export function useSetReadingState() {
  const queryClient = useQueryClient();

  return async (bookId: number, readingState: Partial<ReadingState>) => {
    const queryKey = queryKeys.book.detail(bookId);

    // A read that started before the mutation must not overwrite its result
    await queryClient.cancelQueries({ queryKey });
    queryClient.setQueryData<Book>(queryKey, (book) => book && { ...book, ...readingState });
  };
}

export function useBook(bookId: Ref<number>) {
  const { data: book, error: loadFailure } = useQuery({
    queryKey: computed(() => queryKeys.book.detail(bookId.value)),
    queryFn: () => getBook(bookId.value),
    // An invalid id loads nothing
    enabled: () => bookId.value > 0,
  });

  const error = computed(() => {
    const failure = loadFailure.value;
    if (!failure) {
      return "";
    }

    return failure instanceof Error ? failure.message : "Failed to load book. Please try again.";
  });

  return { book, error };
}
