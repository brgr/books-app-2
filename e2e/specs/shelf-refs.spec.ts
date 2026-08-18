import { expect, test } from "@playwright/test";
import { authenticate } from "../support/auth";
import { createLibraryBook, setShelf } from "../support/api";

const STARTED_TITLE = "E2E Tagged Shelf Ref";

test.beforeAll(async () => {
  const bookId = await createLibraryBook(STARTED_TITLE, "E2E Author");
  await setShelf(bookId, "started");
});

test("the reading shelf uses its tagged API ref", async ({ context, page }) => {
  await authenticate(context);

  const startedShelfResponse = page.waitForResponse((response) => {
    const url = new URL(response.url());
    return (
      response.request().method() === "GET" &&
      url.pathname === "/api/shelves/reading:started/books"
    );
  });

  await page.goto("/");

  expect((await startedShelfResponse).status()).toBe(200);

  const readingNow = page.locator(".book-shelf", {
    has: page.getByRole("heading", { name: "Reading now" }),
  });
  await expect(
    readingNow.getByText(STARTED_TITLE, { exact: true }),
  ).toBeVisible();
});
