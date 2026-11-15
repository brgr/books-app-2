import { useMutation } from "@tanstack/vue-query";
import { setNotes } from "../api/books";
import { invalidateAfter } from "../query/invalidate";
import { useSetUserBook } from "./useBook";

export function useSaveBookNotes() {
  const setUserBook = useSetUserBook();

  return useMutation({
    mutationFn: ({ bookId, notes }: { bookId: number; notes: string }) => setNotes(bookId, notes),
    onSuccess: async (userBook, { bookId }) => {
      await setUserBook(bookId, userBook);
      await invalidateAfter.notesSaved(bookId);
    },
  });
}
