import { useMutation } from "@tanstack/vue-query";
import { clearRating, setRating } from "../api/books";
import { invalidateAfter } from "../query/invalidate";
import { useSetUserBook } from "./useBook";

export function useSaveBookRating() {
  const setUserBook = useSetUserBook();

  return useMutation({
    mutationFn: async ({ bookId, rating }: { bookId: number; rating: number | null }) => {
      if (rating !== null) {
        return setRating(bookId, rating);
      }

      // Clearing answers with no content, and only the rating changes
      await clearRating(bookId);
      return null;
    },
    onSuccess: async (userBook, { bookId }) => {
      await setUserBook(bookId, (current) => userBook ?? { ...current, rating: null });
      await invalidateAfter.ratingSaved(bookId);
    },
  });
}
