import { useQuery, useQueryClient } from "@tanstack/vue-query";
import { computed, type Ref } from "vue";
import { useRoute } from "vue-router";
import { getBook } from "../api/books";
import type { Book } from "../api/types";
import { queryKeys } from "../query/keys";

/** The book id in the current route's `id` parameter, or 0 when it isn't a number. */
export function useRouteBookId() {
  const route = useRoute();

  return computed(() => {
    const id = parseInt(route.params.id as string);
    return isNaN(id) ? 0 : id;
  });
}

/**
 * @param initialData Synchronous data already on screen elsewhere. Shown until the book has been fetched, unless the
 *   book is already cached.
 */
export function useBook(bookId: Ref<number>, initialData?: () => Book | undefined) {
  const queryClient = useQueryClient();

  const { data: book, error: loadFailure } = useQuery({
    queryKey: computed(() => queryKeys.book.detail(bookId.value)),
    queryFn: () => getBook(bookId.value),
    // An invalid id loads nothing
    enabled: () => bookId.value > 0,
    initialData,
  });

  /** Replaces the cached book, e.g. with what a saved mutation answered. */
  async function setBook(next: Book) {
    const queryKey = queryKeys.book.detail(next.id);

    // A read that started before the mutation must not overwrite its result
    await queryClient.cancelQueries({ queryKey });
    queryClient.setQueryData(queryKey, next);
  }

  const error = computed(() => {
    const failure = loadFailure.value;
    if (!failure) {
      return "";
    }

    return failure instanceof Error ? failure.message : "Failed to load book. Please try again.";
  });

  return { book, error, setBook };
}
