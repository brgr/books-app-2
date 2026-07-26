import { expect, test } from "@playwright/test";
import { authenticate } from "../support/auth";
import { createLibraryBook, setShelf } from "../support/api";

const READING_NOW_TITLE = "E2E Buried Reading";

/**
 * // TODO: Update this text here, once fixed
 * "Reading now" only shows currently-reading books that happen to sit on the first loaded
 * page of the "To Read" list. A currently-reading book further down the list is invisible on
 * the front page until enough pages auto-load — normally only triggered by scrolling far down
 * or by typing into search. It should be in "Reading now" on first paint.
 */
test.beforeAll(async () => {
  // Create the book AFTER the baseline fixture is seeded: the API appends new library books to
  // the end of "To Read", so it lands on a later page. Only THEN mark it started. That keeps
  // its list position, so it stays buried past the first loaded page. This is the exact state
  // the "Reading now" bug used to miss.
  const bookId = await createLibraryBook(READING_NOW_TITLE, "E2E Author");
  await setShelf(bookId, "started");
});

test("currently-reading book below the first page shows in 'Reading now'", async ({
  context,
  page,
}) => {
  await authenticate(context);

  await page.goto("/");

  // Wait for the first page of the "To Read" shelf to render, but do NOT scroll or search.
  // This is the plain "open the app" view the user sees.
  await expect(
    page.locator(".book-card, .grid-cover, .books-list > *").first(),
  ).toBeVisible();

  // The "Reading now" section must contain the currently-reading book, even though it sorts
  // far down the "To Read" list and is not on the first loaded page.
  const readingNow = page.locator(".shelf-section", {
    has: page.getByRole("heading", { name: "Reading now" }),
  });

  await expect(
    readingNow.getByRole("heading", {
      level: 3,
      name: READING_NOW_TITLE,
      exact: true,
    }),
  ).toBeVisible();
});
