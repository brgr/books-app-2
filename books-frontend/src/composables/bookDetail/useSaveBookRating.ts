import { useMutation } from "@tanstack/vue-query";
import { clearRating, setRating } from "../../api/books";
import { invalidateAfter } from "../../query/invalidate";
import { useSetReadingState } from "../useBook";

export function useSaveBookRating() {
  const setReadingState = useSetReadingState();

  return useMutation({
    mutationFn: async ({ bookId, rating }: { bookId: number; rating: number | null }) => {
      if (rating !== null) {
        return setRating(bookId, rating);
      }

      // Clearing answers with no content, and only the rating changes
      await clearRating(bookId);
      return null;
    },
    onSuccess: async (readingState, { bookId }) => {
      await setReadingState(bookId, readingState ?? { rating: null });
      await invalidateAfter.ratingSaved(bookId);
    },
  });
}
