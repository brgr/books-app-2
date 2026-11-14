export const queryKeys = {
  shelves: {
    all: () => ["shelves"] as const,
    list: () => ["shelves", "list"] as const,
  },
  book: {
    customShelves: (bookId: number) => ["books", bookId, "custom-shelves"] as const,
  },
};
