export const ReadingStatus = {
  WANT_TO_READ: 'want_to_read',
  STARTED: 'started',
  FINISHED: 'finished',
  ABANDONED: 'abandoned',
} as const

export type ReadingStatus = typeof ReadingStatus[keyof typeof ReadingStatus]

export interface User {
  id: number
  username: string
  created_at: string
}

export interface UserBook {
  id: number
  user_id: number
  book_id: number
  status: ReadingStatus
  started_at: string | null
  finished_at: string | null
  notes: string | null
  created_at: string
  updated_at: string
}

export interface Book {
  id: number
  title: string
  author: string
  isbn: string | null
  description: string | null
  published_date: string | null
  page_count: number | null
  cover_image_url: string | null
  created_at: string
  updated_at: string
  user_status: UserBook | null
}

export interface PaginatedBooks {
  items: Book[]
  total: number
  page: number
  page_size: number
  pages: number
}

export interface BookCreate {
  title: string
  author: string
  isbn?: string
  description?: string
  published_date?: string
  page_count?: number
  cover_image_url?: string
}

export interface BookUpdate {
  title?: string
  author?: string
  isbn?: string
  description?: string
  published_date?: string
  page_count?: number
  cover_image_url?: string
}

export interface UserBookStatusUpdate {
  status: ReadingStatus
  notes?: string
}

export interface GoogleBookResult {
  title: string
  author: string
  isbn: string | null
  description: string | null
  published_date: string | null
  page_count: number | null
  thumbnail: string | null
  google_books_id: string | null
}

export const BookEventType = {
  ADDED_TO_LIBRARY: 'added_to_library',
  STARTED_READING: 'started_reading',
  FINISHED_READING: 'finished_reading',
} as const

export type BookEventType = typeof BookEventType[keyof typeof BookEventType]

export interface BookEvent {
  id: string
  event_type: BookEventType
  occurred_at: string
}
