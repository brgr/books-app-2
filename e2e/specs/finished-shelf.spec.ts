import { expect, test } from "@playwright/test";
import { authenticate } from "../support/auth";
import { createLibraryBook, setShelf } from "../support/api";

const FINISHED_TITLE = "E2E Finished Book";

/**
 * Regression: the Finished shelf showed "No finished books yet" even though finished books
 * exist. This spec seeds a finished book, then asserts it shows on the Finished shelf.
 */
test.beforeAll(async () => {
  // A finished book: create it, then walk it through the real reading lifecycle (started ->
  // finished), which relocates it from "To Read" to the "Finished" shelf.
  const bookId = await createLibraryBook(FINISHED_TITLE, "E2E Author");
  await setShelf(bookId, "started");
  await setShelf(bookId, "finished");
});

test("finished book is visible on the Finished shelf", async ({
  context,
  page,
}) => {
  await authenticate(context);

  await page.goto("/");

  // The default "To Read" shelf must be fully loaded first, so booksData holds a multi-page result and the
  // infinite-scroll sentinel is live (hasMore === true). This mirrors the real user flow: browse To Read, then tap
  // Finished.
  await expect(
    page.locator(".book-card, .grid-cover, .books-list > *").first(),
  ).toBeVisible();
  await page.waitForLoadState("networkidle");

  // Switch to the "Finished" shelf.
  await page.getByText("Finished", { exact: true }).first().click();

  // The finished book must appear on the Finished shelf.
  await expect(
    page.getByText(FINISHED_TITLE, { exact: false }).first(),
  ).toBeVisible();

  // ...and the empty state must NOT be shown.
  await expect(page.getByText("No finished books yet.")).toHaveCount(0);
});
