import { ref } from "vue";
import { createBook } from "../api/books";
import type { GoogleBookResult } from "../api/types";
import { invalidateCache } from "../cache/invalidate";

/**
 * Drives the "add a book" flow shared by the book list and detail views:
 * opening the search modal, creating the selected book, and invalidating
 * cached lists. `onAdded` runs after a successful add for view-specific
 * follow-up (e.g. refreshing the list or navigating away).
 */
export function useAddBook(onAdded?: () => unknown | Promise<unknown>) {
  const showSearchModal = ref(false);
  const addingBook = ref(false);

  function openSearch() {
    showSearchModal.value = true;
  }

  function closeSearch() {
    if (addingBook.value) return;
    showSearchModal.value = false;
  }

  async function selectBook(book: GoogleBookResult) {
    if (addingBook.value) return;
    addingBook.value = true;
    try {
      await createBook({
        title: book.title,
        author: book.author,
        isbn: book.isbn || undefined,
        description: book.description || undefined,
        published_date: book.published_date || undefined,
        page_count: book.page_count ?? undefined,
        cover_image_url: book.thumbnail || undefined,
      });
      await invalidateCache.bookAdded();
      await onAdded?.();
      showSearchModal.value = false;
    } catch (err: any) {
      console.error("Failed to add book:", err);
      alert(err.response?.data?.detail || "Failed to add book. Please try again.");
    } finally {
      addingBook.value = false;
    }
  }

  return { showSearchModal, addingBook, openSearch, closeSearch, selectBook };
}
