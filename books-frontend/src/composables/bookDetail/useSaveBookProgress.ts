import { useMutation } from "@tanstack/vue-query";
import { addBookProgress } from "../../api/books";
import type { BookProgressUpdate } from "../../api/types";
import { invalidateAfter } from "../../query/invalidate";
import { useSetReadingState } from "../useBook";

export function useSaveBookProgress() {
  const setReadingState = useSetReadingState();

  return useMutation({
    mutationFn: ({ bookId, progress }: { bookId: number; progress: BookProgressUpdate }) =>
      addBookProgress(bookId, progress),
    onSuccess: async (readingState, { bookId }) => {
      await setReadingState(bookId, readingState);
      // Stay pending until the timeline shows the new progress
      await invalidateAfter.progressSaved(bookId);
    },
    onError: (err) => {
      console.error("Failed to save progress:", err);
      alert("Failed to save progress");
    },
  });
}
