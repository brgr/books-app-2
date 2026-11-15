import type { ShelfRef } from "../api/types";

export const queryKeys = {
  shelves: {
    all: () => ["shelves"] as const,
    list: () => ["shelves", "list"] as const,
    books: (shelf: ShelfRef, pageSize: number) => ["shelves", shelf, "books", { pageSize }] as const,
  },
  book: {
    root: () => ["books"] as const,
    all: (bookId: number) => ["books", bookId] as const,
    detail: (bookId: number) => ["books", bookId, "detail"] as const,
    events: (bookId: number) => ["books", bookId, "events"] as const,
    customShelves: (bookId: number) => ["books", bookId, "custom-shelves"] as const,
  },
};
