import type { Book, BookCreate } from "../../api/types";
import { isPendingCover } from "./cover/pendingCoverUploads";

export interface BookFormData {
  title: string;
  author: string;
  isbn: string;
  page_count: string | number;
  published_date: string;
  description: string;
  cover_image_url: string;
}

export function emptyBookForm(): BookFormData {
  return {
    title: "",
    author: "",
    isbn: "",
    page_count: "",
    published_date: "",
    description: "",
    cover_image_url: "",
  };
}

export function bookToForm(book: Book): BookFormData {
  return {
    title: book.title,
    author: book.author,
    isbn: book.isbn ?? "",
    page_count: book.page_count ?? "",
    published_date: book.published_date?.split("T")[0] ?? "",
    description: book.description ?? "",
    cover_image_url: book.cover_image_url ?? "",
  };
}

export function formToPayload(form: BookFormData): BookCreate {
  return {
    title: form.title.trim(),
    author: form.author.trim(),
    isbn: form.isbn.trim() || undefined,
    page_count: form.page_count === "" ? undefined : Number(form.page_count),
    published_date: form.published_date || undefined,
    description: form.description.trim() || undefined,
    // Staged files are committed through the cover upload endpoint.
    cover_image_url: isPendingCover(form.cover_image_url) ? undefined : form.cover_image_url || undefined,
  };
}
