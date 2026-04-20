export const cacheKeys = {
  lists: () => 'lists',
  listBooks: (listId: number, page: number, pageSize: number) =>
    `lists:${listId}:books:page=${page}&pageSize=${pageSize}`,
  book: (id: number) => `books:${id}`,
  bookEvents: (id: number) => `books:${id}:events`,
}
