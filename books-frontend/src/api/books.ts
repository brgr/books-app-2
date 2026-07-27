import { apiClient } from "./client";
import type {
  Book,
  BookCreate,
  BookEvent,
  BookProgressUpdate,
  BookUpdate,
  CoverSearchResult,
  CoverUpgradeJob,
  GoogleBookResult,
  ImportRecord,
  PaginatedBooks,
  Shelf,
  ShelfReorderRequest,
  UserBook,
  UserBookShelfUpdate,
} from "./types";

export async function getBooks(page = 1, pageSize = 20): Promise<PaginatedBooks> {
  const response = await apiClient.get<PaginatedBooks>("/books", {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function getShelves(): Promise<Shelf[]> {
  const response = await apiClient.get<Shelf[]>("/shelves");
  return response.data;
}

export async function getShelfBooks(shelfId: number, page = 1, pageSize = 20): Promise<PaginatedBooks> {
  const response = await apiClient.get<PaginatedBooks>(`/shelves/${shelfId}/books`, {
    params: { page, page_size: pageSize },
  });
  return response.data;
}

export async function reorderShelfItem(shelfId: number, payload: ShelfReorderRequest): Promise<void> {
  await apiClient.post(`/shelves/${shelfId}/items/reorder`, payload);
}

export async function getBook(id: number): Promise<Book> {
  const response = await apiClient.get<Book>(`/books/${id}`);
  return response.data;
}

export async function createBook(book: BookCreate): Promise<Book> {
  const response = await apiClient.post<Book>("/books", book);
  return response.data;
}

export async function updateBook(id: number, book: BookUpdate): Promise<Book> {
  const response = await apiClient.put<Book>(`/books/${id}`, book);
  return response.data;
}

export async function deleteBook(id: number): Promise<void> {
  await apiClient.delete(`/books/${id}`);
}

export async function deleteAllBooks(): Promise<void> {
  await apiClient.delete("/books");
}

export async function setShelf(bookId: number, data: UserBookShelfUpdate): Promise<UserBook> {
  const response = await apiClient.put<UserBook>(`/books/${bookId}/shelf`, data);
  return response.data;
}

export async function removeFromLibrary(bookId: number): Promise<void> {
  await apiClient.delete(`/books/${bookId}/shelf`);
}

export async function searchGoogleBooks(query: string): Promise<GoogleBookResult[]> {
  const response = await apiClient.get<GoogleBookResult[]>("/books/search", {
    params: { q: query },
  });
  return response.data;
}

export async function searchBookCovers(params: {
  title?: string;
  author?: string;
  isbn?: string;
}): Promise<CoverSearchResult[]> {
  const response = await apiClient.get<CoverSearchResult[]>("/books/search-covers", {
    params,
  });
  return response.data;
}

export async function uploadBookCover(bookId: number, file: File): Promise<Book> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<Book>(`/books/${bookId}/cover`, formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function startCoverUpgradeSearch(bookId: number): Promise<CoverUpgradeJob> {
  const response = await apiClient.post<CoverUpgradeJob>(`/books/${bookId}/cover-upgrade-search`);
  return response.data;
}

export async function getCoverUpgradeSearch(bookId: number, jobId: string): Promise<CoverUpgradeJob> {
  const response = await apiClient.get<CoverUpgradeJob>(`/books/${bookId}/cover-upgrade-search/${jobId}`);
  return response.data;
}

export async function getBookEvents(bookId: number): Promise<BookEvent[]> {
  const response = await apiClient.get<BookEvent[]>(`/books/${bookId}/events`);
  return response.data;
}

export async function addBookProgress(bookId: number, data: BookProgressUpdate): Promise<UserBook> {
  const response = await apiClient.post<UserBook>(`/books/${bookId}/progress`, data);
  return response.data;
}

export async function importReadingList(file: File): Promise<{ imported: number }> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await apiClient.post<{ imported: number }>("/import/reading-list", formData, {
    headers: { "Content-Type": "multipart/form-data" },
  });
  return response.data;
}

export async function getImports(): Promise<ImportRecord[]> {
  const response = await apiClient.get<ImportRecord[]>("/imports");
  return response.data;
}
