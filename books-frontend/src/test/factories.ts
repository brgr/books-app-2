import { type Book, ReadingShelf } from "../api/types";

export function makeBook(overrides: Partial<Book> = {}): Book {
  return {
    id: 1,
    title: "Dune",
    author: "Frank Herbert",
    isbn: null,
    google_books_id: null,
    description: null,
    published_date: null,
    page_count: null,
    cover_image_url: null,
    cover_thumbnail_url: null,
    shelf: ReadingShelf.WANT_TO_READ,
    started_at: null,
    finished_at: null,
    notes: null,
    progress: null,
    rating: null,
    ...overrides,
  };
}
