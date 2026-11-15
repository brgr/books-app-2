import { useQuery } from "@tanstack/vue-query";
import { computed, type Ref } from "vue";
import { getBookEvents } from "../api/books";
import { queryKeys } from "../query/keys";
import { useBook } from "./useBook";

export function useBookDetail(bookId: Ref<number>) {
  const { book, error } = useBook(bookId);

  const { data: events } = useQuery({
    queryKey: computed(() => queryKeys.book.events(bookId.value)),
    queryFn: () => getBookEvents(bookId.value),
    enabled: () => bookId.value > 0,
  });

  return { book, events, error };
}
