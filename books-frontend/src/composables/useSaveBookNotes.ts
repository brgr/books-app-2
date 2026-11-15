import { useMutation } from "@tanstack/vue-query";
import { setShelf } from "../api/books";
import type { ReadingShelf } from "../api/types";
import { invalidateAfter } from "../query/invalidate";
import { useSetUserBook } from "./useBook";

type NotesChange = { bookId: number; shelf: ReadingShelf; notes: string };

export function useSaveBookNotes() {
  const setUserBook = useSetUserBook();

  return useMutation({
    // Notes are saved along with the shelf, which stays as it is
    mutationFn: ({ bookId, shelf, notes }: NotesChange) => setShelf(bookId, { shelf, notes }),
    onSuccess: async (userBook, { bookId }) => {
      await setUserBook(bookId, userBook);
      await invalidateAfter.notesSaved(bookId);
    },
  });
}
