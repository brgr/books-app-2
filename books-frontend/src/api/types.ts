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
  current_page: number | null
  created_at: string
  updated_at: string
}

export interface BookList {
  id: number
  name: string
}

export interface BookListReorderRequest {
  moved_book_id: number
  before_book_id?: number | null
  after_book_id?: number | null
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
  cover_thumbnail_url: string | null
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
  occurred_at?: string
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
  NOTE_SET: 'note_set',
  PROGRESS_SET: 'progress_set',
} as const

export type BookEventType = typeof BookEventType[keyof typeof BookEventType]

export interface BookEvent {
  id: string
  event_type: BookEventType
  occurred_at: string
  note?: string | null
  page?: number | null
  import_id?: number | null
}

export interface BookProgressUpdate {
  page: number
}

export interface ImportRecord {
  id: number
  filename: string | null
  occurred_at: string
  imported_count: number
  skipped_count: number
}

export interface CoverSearchResult {
  title: string
  author: string | null
  isbn: string | null
  thumbnail: string
  image_url: string
  google_books_id: string | null
}

export interface CoverUpgradeCandidate {
  image_url: string
  thumbnail_url: string
  width: number
  height: number
  source: string
  phash_distance: number
  match_quality: 'exact' | 'likely'
  size_ratio: number
}

export interface CoverUpgradeJob {
  job_id: string
  status: 'running' | 'done' | 'failed'
  results: CoverUpgradeCandidate[]
  error?: string | null
}
