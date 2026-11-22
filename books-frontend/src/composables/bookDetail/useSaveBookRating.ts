import { useMutation } from "@tanstack/vue-query";
import { clearRating, setRating } from "../../api/books";
import { invalidateAfter } from "../../query/invalidate";
import { useSetBook } from "../useBook";

export function useSaveBookRating() {
  const setBook = useSetBook();

  return useMutation({
    mutationFn: async ({ bookId, rating }: { bookId: number; rating: number | null }) => {
      if (rating !== null) {
        return setRating(bookId, rating);
      }

      // Clearing answers with no content, and only the rating changes
      await clearRating(bookId);
      return null;
    },
    onSuccess: async (book, { bookId }) => {
      await setBook(bookId, book ?? { rating: null });
      await invalidateAfter.ratingSaved(bookId);
    },
  });
}
