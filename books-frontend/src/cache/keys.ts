import type { ShelfName } from "../api/types";

const SHELVES_PREFIX = "shelves:";
const bookPrefix = (id: number) => `books:${id}`;

export const cacheKeys = {
  shelfBooks: (shelf: ShelfName, page: number, pageSize: number) =>
    `${SHELVES_PREFIX}${shelf}:books:page=${page}&pageSize=${pageSize}`,
  // Covers every cached page of a shelf (any page/pageSize), for invalidating the whole shelf at once
  shelfBooksPrefix: (shelf: ShelfName) => `${SHELVES_PREFIX}${shelf}:books:`,
  book: bookPrefix,
  bookEvents: (id: number) => `${bookPrefix(id)}:events`,

  // Prefixes for bulk invalidation
  shelvesPrefix: () => SHELVES_PREFIX,
};
