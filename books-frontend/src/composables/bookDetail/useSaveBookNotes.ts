import { useMutation } from "@tanstack/vue-query";
import { setNotes } from "../../api/books";
import { invalidateAfter } from "../../query/invalidate";
import { useSetReadingState } from "../useBook";

export function useSaveBookNotes() {
  const setReadingState = useSetReadingState();

  return useMutation({
    mutationFn: ({ bookId, notes }: { bookId: number; notes: string }) => setNotes(bookId, notes),
    onSuccess: async (readingState, { bookId }) => {
      await setReadingState(bookId, readingState);
      await invalidateAfter.notesSaved(bookId);
    },
  });
}
