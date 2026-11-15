import { useMutation } from "@tanstack/vue-query";
import { addBookProgress } from "../api/books";
import type { BookProgressUpdate } from "../api/types";
import { invalidateAfter } from "../query/invalidate";
import { useSetUserBook } from "./useBook";

export function useSaveBookProgress() {
  const setUserBook = useSetUserBook();

  return useMutation({
    mutationFn: ({ bookId, progress }: { bookId: number; progress: BookProgressUpdate }) =>
      addBookProgress(bookId, progress),
    onSuccess: async (userBook, { bookId }) => {
      await setUserBook(bookId, userBook);
      // Stay pending until the timeline shows the new progress
      await invalidateAfter.progressSaved(bookId);
    },
    onError: (err) => {
      console.error("Failed to save progress:", err);
      alert("Failed to save progress");
    },
  });
}
