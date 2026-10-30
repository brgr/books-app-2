import type { Book } from "../api/types";

let pendingPreview: { book: Book } | null = null;

/** Hand the selected book to the detail view for this navigation only. */
export async function navigateWithBookPreview(book: Book, navigate: () => Promise<unknown>) {
  const preview = { book };
  pendingPreview = preview;
  
  try {
    await navigate();
  } finally {
    // Also release unused data if navigation was cancelled or failed.
    if (pendingPreview === preview) {
      pendingPreview = null;
    }
  }
}

export function takeBookPreview(bookId: number): Book | null {
  const preview = pendingPreview;
  pendingPreview = null;
  
  return preview?.book.id === bookId ? preview.book : null;
}
