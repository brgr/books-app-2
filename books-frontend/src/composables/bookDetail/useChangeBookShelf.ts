import { useMutation } from "@tanstack/vue-query";
import { setShelf } from "../../api/books";
import { ReadingDatePrecision, type ReadingDateValue, type ReadingShelf } from "../../api/types";
import { invalidateAfter } from "../../query/invalidate";
import { localDayValue } from "../../utils/date";
import { useSetReadingState } from "../useBook";

type ShelfChange = { bookId: number; shelf: ReadingShelf; readingDate?: ReadingDateValue };

export function useChangeBookShelf() {
  const setReadingState = useSetReadingState();

  return useMutation({
    mutationFn: ({ bookId, shelf, readingDate }: ShelfChange) =>
      setShelf(bookId, {
        shelf,
        reading_date: readingDate ?? { value: localDayValue(new Date()), precision: ReadingDatePrecision.DAY },
      }),
    onSuccess: async (readingState, { bookId }) => {
      await setReadingState(bookId, readingState);
      await invalidateAfter.shelfChanged(bookId);
    },
    onError: (err) => {
      console.error("Failed to update shelf:", err);
      alert("Failed to update shelf");
    },
  });
}
