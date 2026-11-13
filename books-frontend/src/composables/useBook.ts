import { computed, type Ref } from "vue";
import { useRoute } from "vue-router";
import { getBook } from "../api/books";
import type { Book } from "../api/types";
import { cacheKeys } from "../cache/keys";
import { useCachedQuery } from "./useCachedQuery";

/** The book id in the current route's `id` parameter, or 0 when it isn't a number. */
export function useRouteBookId() {
  const route = useRoute();

  return computed(() => {
    const id = parseInt(route.params.id as string);
    return isNaN(id) ? 0 : id;
  });
}

export function useBook(bookId: Ref<number>, initialData?: () => Book | null) {
  // An empty key loads nothing, which is what we want for an invalid id
  const {
    data: book,
    error: loadFailure,
    setData: setBook,
  } = useCachedQuery<Book>(
    () => (bookId.value > 0 ? cacheKeys.book(bookId.value) : ""),
    () => getBook(bookId.value),
    { initialData },
  );

  const error = computed(() => {
    const failure = loadFailure.value;
    if (!failure) {
      return "";
    }

    return failure instanceof Error ? failure.message : "Failed to load book. Please try again.";
  });

  return { book, error, setBook };
}
