import { expect, request, test } from "@playwright/test";
import { authenticate, login } from "../support/auth";
import { BACKEND_URL } from "../support/config";

const TEST_PAGE_SIZE = 30;

test("move to bottom uses the whole shelf and scrolling preserves every book", async ({
  context,
  page,
}) => {
  const api = await request.newContext({
    baseURL: BACKEND_URL,
    extraHTTPHeaders: { Authorization: `Bearer ${await login()}` },
  });

  const shelfResponse = await api.post("/api/shelves", {
    data: { name: "E2E paginated reorder" },
  });
  expect(shelfResponse.ok()).toBeTruthy();

  const shelf = await shelfResponse.json();
  const titles = Array.from(
    { length: TEST_PAGE_SIZE * 2 + 5 },
    (_, i) => `Reorder book ${String(i + 1).padStart(2, "0")}`,
  );

  for (const title of titles) {
    const created = await api.post("/api/books", {
      data: { title, author: "Reorder Author" },
    });
    expect(created.ok()).toBeTruthy();

    const added = await api.post(`/api/shelves/${shelf.ref}/books`, {
      data: { book_id: (await created.json()).id },
    });
    expect(added.ok()).toBeTruthy();
  }

  await authenticate(context);

  // Set the page size of this E2E test explicitly. Like this, if we might
  // change the page size in the future, this test will still validate
  // that the reordering works across multiple pages of books.
  await page.route(`**/api/shelves/${shelf.ref}/books?*`, async (route) => {
    const url = new URL(route.request().url());
    url.searchParams.set("page_size", String(TEST_PAGE_SIZE));
    await route.continue({ url: url.toString() });
  });

  await page.goto(`/shelves/custom/${shelf.ref.split(":")[1]}`);
  const cards = page.locator(".book-card");
  await expect(cards).toHaveCount(TEST_PAGE_SIZE);
  await cards.first().getByRole("button", { name: "Book actions" }).click();
  const moved = page.waitForResponse(
    (response) =>
      response.url().endsWith("/items/reorder") &&
      response.request().method() === "POST",
  );
  await page.getByRole("menuitem", { name: "Move to Bottom" }).click();
  expect((await moved).ok()).toBeTruthy();

  // Check that the order is correct after moving the first book to the bottom
  const orderResponse = await api.get(
    `/api/shelves/${shelf.ref}/books?page_size=100`,
  );
  const order = (await orderResponse.json()).items.map(
    (book: { title: string }) => book.title,
  );
  expect(order).toEqual([...titles.slice(1), titles[0]]);
  await expect(cards.first()).toContainText(titles[1]);
  await expect(
    page.getByRole("heading", { name: titles[0], exact: true }),
  ).toHaveCount(0);

  // Scroll to the bottom of the shelf and check that all books are present
  while ((await cards.count()) < titles.length) {
    const count = await cards.count();
    await cards.last().scrollIntoViewIfNeeded();
    await expect.poll(() => cards.count()).toBeGreaterThan(count);
  }
  await expect(cards.locator("h3")).toHaveText([...titles.slice(1), titles[0]]);

  // Move the last book to the top and check that the order is correct
  await cards.last().getByRole("button", { name: "Book actions" }).click();
  await page.getByRole("menuitem", { name: "Move to Top" }).click();
  await expect(cards.locator("h3")).toHaveText(titles);
  await page.reload();
  await expect(cards.first()).toContainText(titles[0]);
  await api.dispose();
});
