import { type Book, ReadingShelf, type UserBook } from "../api/types";

export function makeUserBook(overrides: Partial<UserBook> = {}): UserBook {
  return {
    id: 1,
    user_id: 1,
    book_id: 1,
    shelf: ReadingShelf.WANT_TO_READ,
    started_at: null,
    finished_at: null,
    notes: null,
    current_page: null,
    current_percent: null,
    rating: null,
    created_at: "",
    updated_at: "",
    ...overrides,
  };
}

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
    created_at: "",
    updated_at: "",
    user_book: makeUserBook({ book_id: overrides.id ?? 1 }),
    ...overrides,
  };
}
