import { apiClient } from './client'
import type { Book, PaginatedBooks, BookCreate, BookUpdate, UserBookStatusUpdate, UserBook, GoogleBookResult, BookEvent } from './types'

export async function getBooks(page = 1, pageSize = 20): Promise<PaginatedBooks> {
  const response = await apiClient.get<PaginatedBooks>('/books', {
    params: { page, page_size: pageSize },
  })
  return response.data
}

export async function getBook(id: number): Promise<Book> {
  const response = await apiClient.get<Book>(`/books/${id}`)
  return response.data
}

export async function createBook(book: BookCreate): Promise<Book> {
  const response = await apiClient.post<Book>('/books', book)
  return response.data
}

export async function updateBook(id: number, book: BookUpdate): Promise<Book> {
  const response = await apiClient.put<Book>(`/books/${id}`, book)
  return response.data
}

export async function deleteBook(id: number): Promise<void> {
  await apiClient.delete(`/books/${id}`)
}

export async function setReadingStatus(bookId: number, data: UserBookStatusUpdate): Promise<UserBook> {
  const response = await apiClient.put<UserBook>(`/books/${bookId}/status`, data)
  return response.data
}

export async function removeReadingStatus(bookId: number): Promise<void> {
  await apiClient.delete(`/books/${bookId}/status`)
}

export async function searchGoogleBooks(query: string): Promise<GoogleBookResult[]> {
  const response = await apiClient.get<GoogleBookResult[]>('/books/search', {
    params: { q: query },
  })
  return response.data
}

export async function getBookEvents(bookId: number): Promise<BookEvent[]> {
  const response = await apiClient.get<BookEvent[]>(`/books/${bookId}/events`)
  return response.data
}
