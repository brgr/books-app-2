const SHELVES_PREFIX = "shelves:";
const bookPrefix = (id: number) => `books:${id}`;

export const cacheKeys = {
  shelves: () => "shelves",
  shelfBooks: (shelfId: number, page: number, pageSize: number) =>
    `${SHELVES_PREFIX}${shelfId}:books:page=${page}&pageSize=${pageSize}`,
  // Covers every cached page of a shelf (any page/pageSize), for invalidating the whole shelf at once
  shelfBooksPrefix: (shelfId: number) => `${SHELVES_PREFIX}${shelfId}:books:`,
  book: bookPrefix,
  bookEvents: (id: number) => `${bookPrefix(id)}:events`,

  // Prefixes for bulk invalidation
  shelvesPrefix: () => SHELVES_PREFIX,
  bookPrefix,
};
