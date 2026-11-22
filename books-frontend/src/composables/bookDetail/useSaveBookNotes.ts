import { useMutation } from "@tanstack/vue-query";
import { setNotes } from "../../api/books";
import { invalidateAfter } from "../../query/invalidate";
import { useSetBook } from "../useBook";

export function useSaveBookNotes() {
  const setBook = useSetBook();

  return useMutation({
    mutationFn: ({ bookId, notes }: { bookId: number; notes: string }) => setNotes(bookId, notes),
    onSuccess: async (book, { bookId }) => {
      await setBook(bookId, book);
      await invalidateAfter.notesSaved(bookId);
    },
  });
}
