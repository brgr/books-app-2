export const queryKeys = {
  shelves: {
    all: () => ["shelves"] as const,
    list: () => ["shelves", "list"] as const,
  },
  book: {
    detail: (bookId: number) => ["books", bookId, "detail"] as const,
    events: (bookId: number) => ["books", bookId, "events"] as const,
    customShelves: (bookId: number) => ["books", bookId, "custom-shelves"] as const,
  },
};
