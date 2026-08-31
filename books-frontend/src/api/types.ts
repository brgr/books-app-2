export const ReadingShelf = {
  WANT_TO_READ: "want_to_read",
  STARTED: "started",
  PAUSED: "paused",
  FINISHED: "finished",
  ABANDONED: "abandoned",
} as const;

export type ReadingShelf = (typeof ReadingShelf)[keyof typeof ReadingShelf];

export const ReadingDatePrecision = {
  DAY: "day",
  MONTH: "month",
  YEAR: "year",
  UNKNOWN: "unknown",
} as const;

export type ReadingDatePrecision = (typeof ReadingDatePrecision)[keyof typeof ReadingDatePrecision];

/** A user-stated calendar date, which may deliberately be partial or unknown. */
export interface ReadingDateValue {
  value: string | null;
  precision: ReadingDatePrecision;
}

/** Address of a built-in reading shelf. */
export type ReadingShelfRef = `reading:${ReadingShelf}`;

/** Address of a custom shelf. */
export type CustomShelfRef = `custom:${number}`;

/** Address of either a built-in reading shelf or a custom shelf. */
export type ShelfRef = ReadingShelfRef | CustomShelfRef;

/**
 * Validates and narrows a shelf reference received from an untyped source such as a route or
 * an API response.
 */
export function parseShelfRef(value: string): ShelfRef {
  const readingPrefix = "reading:";
  const customMatch = /^custom:([1-9]\d*)$/.exec(value);

  if (
    value.startsWith(readingPrefix) &&
    Object.values(ReadingShelf).includes(value.slice(readingPrefix.length) as ReadingShelf)
  ) {
    return value as ReadingShelfRef;
  }

  if (customMatch) {
    return value as CustomShelfRef;
  }

  throw new Error(`Invalid shelf reference: ${value}`);
}

export interface Shelf {
  ref: ShelfRef;
  display_name: string;
  book_count: number;
}

export interface User {
  id: number;
  username: string;
  created_at: string;
}

export interface UserBook {
  id: number;
  user_id: number;
  book_id: number;
  shelf: ReadingShelf;
  started_at: ReadingDateValue | null;
  finished_at: ReadingDateValue | null;
  notes: string | null;
  current_page: number | null;
  current_percent: number | null;
  created_at: string;
  updated_at: string;
}

export interface ShelfReorderRequest {
  moved_book_id: number;
  before_book_id?: number | null;
  after_book_id?: number | null;
}

export interface Book {
  id: number;
  title: string;
  author: string;
  isbn: string | null;
  description: string | null;
  published_date: string | null;
  page_count: number | null;
  cover_image_url: string | null;
  cover_thumbnail_url: string | null;
  created_at: string;
  updated_at: string;
  user_book: UserBook | null;
}

export interface PaginatedBooks {
  items: Book[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
}

export interface BookCreate {
  title: string;
  author: string;
  isbn?: string;
  description?: string;
  published_date?: string;
  page_count?: number;
  cover_image_url?: string;
}

export interface BookUpdate {
  title?: string;
  author?: string;
  isbn?: string;
  description?: string;
  published_date?: string;
  page_count?: number;
  cover_image_url?: string;
}

export interface UserBookShelfUpdate {
  shelf: ReadingShelf;
  notes?: string;
  reading_date?: ReadingDateValue;
}

export interface GoogleBookResult {
  title: string;
  author: string;
  isbn: string | null;
  description: string | null;
  published_date: string | null;
  page_count: number | null;
  thumbnail: string | null;
  google_books_id: string | null;
}

export const BookEventType = {
  ADDED_TO_LIBRARY: "added_to_library",
  STARTED_READING: "started_reading",
  FINISHED_READING: "finished_reading",
  NOTE_SET: "note_set",
  PROGRESS_SET: "progress_set",
} as const;

export type BookEventType = (typeof BookEventType)[keyof typeof BookEventType];

export interface BookEvent {
  id: string;
  event_type: BookEventType;
  occurred_at: string;
  reading_date?: ReadingDateValue | null;
  note?: string | null;
  page?: number | null;
  import_id?: number | null;
}

export interface BookProgressUpdate {
  page?: number;
  percent?: number;
}

export interface ImportRecord {
  id: number;
  filename: string | null;
  occurred_at: string;
  imported_count: number;
  skipped_count: number;
}

export interface CoverSearchResult {
  title: string;
  author: string | null;
  isbn: string | null;
  thumbnail: string;
  image_url: string;
  google_books_id: string | null;
}

export interface CoverUpgradeCandidate {
  image_url: string;
  thumbnail_url: string;
  width: number;
  height: number;
  source: string;
  phash_distance: number;
  match_quality: "exact" | "likely";
  size_ratio: number;
}

export interface CoverUpgradeJob {
  job_id: string;
  status: "running" | "done" | "failed";
  results: CoverUpgradeCandidate[];
  error?: string | null;
}
