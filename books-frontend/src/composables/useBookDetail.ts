import { ref, toRaw, type Ref } from "vue";
import { addBookProgress, clearRating, getBookEvents, setRating, setShelf } from "../api/books";
import {
  type Book,
  type BookEvent,
  type BookProgressUpdate,
  ReadingDatePrecision,
  type ReadingDateValue,
  type ReadingShelf,
  type UserBook,
} from "../api/types";
import { invalidateCache } from "../cache/invalidate";
import { cacheKeys } from "../cache/keys";
import { takeBookPreview } from "../router/bookPreview";
import { localDayValue } from "../utils/date";
import { useBook } from "./useBook";
import { useCachedQuery } from "./useCachedQuery";

export function useBookDetail(bookId: Ref<number>) {
  const { book, error, setBook } = useBook(bookId, () => takeBookPreview(bookId.value));

  const { data: events, refresh: refreshEvents } = useCachedQuery<BookEvent[]>(
    () => (bookId.value > 0 ? cacheKeys.bookEvents(bookId.value) : ""),
    () => getBookEvents(bookId.value),
  );

  const savingShelf = ref(false);
  const savingReview = ref(false);
  const savingProgress = ref(false);
  const reviewError = ref("");

  /** Rejects when the request fails, leaving it to the caller to tell the user. */
  async function save(
    saving: Ref<boolean>,
    request: (book: Book) => Promise<UserBook>,
    invalidate: (bookId: number) => Promise<void>,
  ) {
    const target = book.value;
    if (!target || saving.value) {
      return;
    }

    saving.value = true;
    try {
      const userBook = await request(target);
      await invalidate(target.id);

      // The user may have moved on to another book while the request was running
      if (bookId.value === target.id) {
        await setBook({ ...(book.value ?? target), user_book: userBook });
        await refreshEvents();
      }
    } finally {
      saving.value = false;
    }
  }

  async function changeShelf(shelf: ReadingShelf, readingDate?: ReadingDateValue) {
    const today = { value: localDayValue(new Date()), precision: ReadingDatePrecision.DAY };

    try {
      await save(
        savingShelf,
        (target) => setShelf(target.id, { shelf, reading_date: readingDate ?? today }),
        invalidateCache.shelfChanged,
      );
    } catch (err) {
      console.error("Failed to update shelf:", err);
      alert("Failed to update shelf");
    }
  }

  async function saveProgress(progress: BookProgressUpdate) {
    try {
      await save(savingProgress, (target) => addBookProgress(target.id, progress), invalidateCache.progressSaved);
    } catch (err) {
      console.error("Failed to save progress:", err);
      alert("Failed to save progress");
    }
  }

  async function saveReview(notes: string, rating: number | null) {
    const id = bookId.value;
    reviewError.value = "";

    try {
      if (notes !== (book.value?.user_book.notes ?? "")) {
        await save(
          savingReview,
          (target) => setShelf(target.id, { shelf: target.user_book.shelf, notes }),
          invalidateCache.notesSaved,
        );
      }

      if (rating !== book.value?.user_book.rating) {
        await save(savingReview, (target) => saveRating(target, rating), invalidateCache.ratingSaved);
      }
    } catch (err) {
      console.error("Failed to save rating and notes:", err);
      if (bookId.value === id) {
        reviewError.value = "Failed to save rating and notes. Please try again.";
      }
    }
  }

  return {
    book,
    events,
    error,
    savingShelf,
    savingReview,
    savingProgress,
    reviewError,
    changeShelf,
    saveProgress,
    saveReview,
  };
}

async function saveRating(book: Book, rating: number | null): Promise<UserBook> {
  if (rating !== null) {
    return setRating(book.id, rating);
  }

  // Clearing answers with no content, and only the rating changes.
  // Copy the underlying data so nested reading dates remain serializable in IndexedDB.
  await clearRating(book.id);
  return { ...toRaw(book.user_book), rating: null };
}
