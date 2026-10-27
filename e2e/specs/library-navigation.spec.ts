import { expect, type Page, test } from "@playwright/test";
import { authenticate } from "../support/auth";

// A deterministic, multi-page library exercises navigation without importing hundreds of books.
async function mockLibrary(page: Page) {
  const books = Array.from({ length: 205 }, (_, index) => ({
    id: index + 1,
    title: `Navigation book ${String(index + 1).padStart(3, "0")}`,
    author: "Navigation author",
    description: null,
    cover_image_url: null,
    cover_thumbnail_url: null,
    user_book: null,
  }));

  const shelves = [
    { ref: "custom:999", display_name: "Navigation shelf", book_count: 205 },
    { ref: "custom:998", display_name: "Other shelf", book_count: 205 },
  ];

  await page.route("**/api/shelves**", async (route) => {
    const url = new URL(route.request().url());

    if (url.pathname === "/api/shelves") {
      await route.fulfill({ json: shelves });
      return;
    }

    if (url.pathname.endsWith("/books")) {
      const number = Number(url.searchParams.get("page") ?? 1);
      const size = Number(url.searchParams.get("page_size") ?? 100);
      const items = /reading:(started|paused)/.test(url.pathname) ? [] : books;

      await route.fulfill({
        json: {
          items: items.slice((number - 1) * size, number * size),
          page: number,
          page_size: size,
          pages: Math.ceil(items.length / size),
          total: items.length,
        },
      });

      return;
    }

    await route.continue();
  });

  await page.route("**/api/books/*", async (route) => {
    const url = new URL(route.request().url());
    const id = Number(url.pathname.split("/").at(-1));
    const book = books.find((item) => item.id === id);

    if (!book) {
      await route.continue();
      return;
    }

    if (route.request().method() === "PUT") {
      Object.assign(book, route.request().postDataJSON());
    }

    await route.fulfill({ json: book });
  });

  await page.route("**/api/books/*/events", (route) =>
    route.fulfill({ json: [] }),
  );

  await page.route("**/api/books/*/custom-shelves", (route) =>
    route.fulfill({ json: [] }),
  );
}

for (const mode of ["list", "grid"] as const) {
  test(`${mode}: return to the same search, pages and mobile scroll position`, async ({
    context,
    page,
  }) => {
    await authenticate(context);
    await mockLibrary(page);

    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/");

    await expect(page.locator(".book-card")).toHaveCount(100);

    if (mode === "grid") {
      await page.getByRole("button", { name: "Grid view" }).click();
    }

    const items = page.locator(mode === "grid" ? ".grid-item" : ".book-card");
    await page.getByPlaceholder("Search for words or #tags").fill("Navigation");
    await page.locator(".infinite-sentinel").scrollIntoViewIfNeeded();
    await expect(items).toHaveCount(200);

    const link = page
      .locator(mode === "grid" ? ".grid-cover-link" : ".book-title-link")
      .nth(149);
    await link.scrollIntoViewIfNeeded();
    const scroll = await page.evaluate(() => window.scrollY);
    await link.click();

    await expect(
      page.getByRole("heading", { name: "Navigation book 150" }),
    ).toBeVisible();
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(0);

    await page.getByRole("link", { name: "Back to shelf" }).click();
    await expect(page).toHaveURL(/\/$/);
    await expect(
      page.getByPlaceholder("Search for words or #tags"),
    ).toHaveValue("Navigation");
    await expect(items).toHaveCount(200);
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(scroll);

    // Browser Back/Forward use the same retained shelf and restore the saved position.
    await page.goForward();
    await expect(
      page.getByRole("heading", { name: "Navigation book 150" }),
    ).toBeVisible();
    await page.goBack();
    await expect(items).toHaveCount(200);
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(scroll);

    // Root and the To Read URL are aliases of the same tab; Finished has its own search.
    await page.getByRole("link", { name: "Finished", exact: true }).click();
    await expect(
      page.getByPlaceholder("Search for words or #tags"),
    ).toHaveValue("");
    await page.getByPlaceholder("Search for words or #tags").fill("book 00");
    await page.getByRole("link", { name: "To Read", exact: true }).click();
    await expect(
      page.getByPlaceholder("Search for words or #tags"),
    ).toHaveValue("Navigation");
    await expect(items).toHaveCount(200);
    await expect.poll(() => page.evaluate(() => window.scrollY)).toBe(scroll);
    await page.getByRole("link", { name: "Finished", exact: true }).click();
    await expect(
      page.getByPlaceholder("Search for words or #tags"),
    ).toHaveValue("book 00");
  });
}

test("custom shelves retain separate searches and return after editing a book", async ({
  context,
  page,
}) => {
  await authenticate(context);
  await mockLibrary(page);
  await page.goto("/shelves/custom/999");
  const search = page.getByPlaceholder("Search for words or #tags");
  await search.fill("book 005");
  await page.getByRole("link", { name: "Shelves", exact: true }).click();
  await page.getByRole("link", { name: "Other shelf" }).click();
  await expect(search).toHaveValue("");
  await search.fill("book 006");
  await page.getByRole("link", { name: "Shelves", exact: true }).click();
  await page.getByRole("link", { name: "Navigation shelf" }).click();
  await expect(search).toHaveValue("book 005");
  await page
    .getByRole("link", { name: "Navigation book 005", exact: true })
    .click();
  await page.getByRole("button", { name: "Edit Book", exact: true }).click();
  await page.getByLabel("Title").fill("Navigation book 005 revised");
  await page.getByRole("button", { name: "Save Book", exact: true }).click();
  await page.getByRole("link", { name: "Back to shelf" }).click();
  await expect(page).toHaveURL(/\/shelves\/custom\/999$/);
  await expect(search).toHaveValue("book 005");
  await expect(
    page.getByRole("link", {
      name: "Navigation book 005 revised",
      exact: true,
    }),
  ).toBeVisible();

  // The login route discards retained views, including searches from the previous session.
  await page.getByRole("button", { name: "Open user menu" }).click();
  await page.getByRole("menuitem", { name: "Logout" }).click();
  await expect(page).toHaveURL(/\/login$/);
  await page.getByLabel("Username").fill("dev");
  await page.getByLabel("Password").fill("devpassword");
  await page.getByRole("button", { name: "Login", exact: true }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.getByRole("link", { name: "Shelves", exact: true }).click();
  await page.getByRole("link", { name: "Navigation shelf" }).click();
  await expect(search).toHaveValue("");
});
