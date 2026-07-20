import { type APIRequestContext, request } from "@playwright/test";
import { BACKEND_URL } from "./config";
import { login } from "./auth";

/** A reading status a library book can be moved to via the API. */
export type ReadingStatus =
  "want_to_read" | "started" | "finished" | "abandoned";

// The dev user's token is stable for the whole run, so get it once and
// share it across the seeding calls.
let tokenPromise: Promise<string> | undefined;

async function backendClient(): Promise<APIRequestContext> {
  const token = await (tokenPromise ??= login());
  return request.newContext({
    baseURL: BACKEND_URL,
    extraHTTPHeaders: { Authorization: `Bearer ${token}` },
  });
}

/**
 * Create a book and add it to the seeded user's library via the real API, returning its id.
 *
 * Mirrors the app's "add book": the new book is appended to the END of the "To Read" list.
 */
export async function createLibraryBook(
  title: string,
  author: string,
): Promise<number> {
  const api = await backendClient();

  try {
    const response = await api.post("/api/books", { data: { title, author } });

    if (!response.ok()) {
      throw new Error(
        `Create book failed: ${response.status()} ${await response.text()}`,
      );
    }

    return (await response.json()).id;
  } finally {
    await api.dispose();
  }
}

/**
 * Move a library book to a reading status (`PUT /books/:id/status`).
 *
 * Moving to "started" keeps the book's existing position in "To Read"; moving to "finished"
 * relocates it to the "Finished" shelf. This is the same endpoint the app calls.
 */
export async function setReadingStatus(
  bookId: number,
  status: ReadingStatus,
): Promise<void> {
  const api = await backendClient();

  try {
    const response = await api.put(`/api/books/${bookId}/status`, {
      data: { status },
    });

    if (!response.ok()) {
      throw new Error(
        `Set status failed: ${response.status()} ${await response.text()}`,
      );
    }
  } finally {
    await api.dispose();
  }
}
