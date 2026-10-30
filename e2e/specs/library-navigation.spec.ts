import { expect, type Page, test } from "@playwright/test";
import { authenticate } from "../support/auth";

// A deterministic, multi-page library exercises navigation without importing hundreds of books.
async function mockLibrary(page: Page, covers = false) {
  const books = Array.from({ length: 205 }, (_, index) => ({
    id: index + 1,
    title: `Navigation book ${String(index + 1).padStart(3, "0")}`,
    author: "Navigation author",
    description: null,
    cover_image_url: covers ? "/preview-cover.svg" : null,
    cover_thumbnail_url: covers ? "/preview-thumbnail.svg" : null,
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
  test(`${mode}: show shelf details and thumbnail while book, timeline and larger cover are pending`, async ({
    context,
    page,
  }) => {
    await authenticate(context);
    await mockLibrary(page, true);
    
    const image =
      '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="449"><rect width="300" height="449" fill="teal"/></svg>';
    // Real thumbnails have rounded dimensions; the full image's ratio can differ slightly.
    const fullImage =
      '<svg xmlns="http://www.w3.org/2000/svg" width="1000" height="1498"><rect width="1000" height="1498" fill="teal"/></svg>';
    await page.route("**/preview-thumbnail.svg", (route) =>
      route.fulfill({ contentType: "image/svg+xml", body: image }),
    );
    
    let finishBook!: () => void;
    let finishCover!: () => void;
    let finishEvents!: () => void;
    const bookReady = new Promise<void>((resolve) => (finishBook = resolve));
    const coverReady = new Promise<void>((resolve) => (finishCover = resolve));
    const eventsReady = new Promise<void>(
      (resolve) => (finishEvents = resolve),
    );
    
    await page.route("**/api/books/1", async (route) => {
      await bookReady;
      await route.fulfill({
        json: {
          id: 1,
          title: "Refreshed book",
          author: "Fresh author",
          cover_thumbnail_url: "/preview-thumbnail.svg",
          cover_image_url: "/preview-cover.svg",
          user_book: null,
        },
      });
    });
    await page.route("**/api/books/1/events", async (route) => {
      await eventsReady;
      await route.fulfill({ json: [] });
    });
    await page.route("**/preview-cover.svg", async (route) => {
      await coverReady;
      await route.fulfill({ contentType: "image/svg+xml", body: fullImage });
    });

    try {
      await page.setViewportSize({ width: 390, height: 844 });
      await page.goto(mode === "list" ? "/" : "/shelves/custom/999");
      
      if (mode === "grid") {
        await page.getByRole("button", { name: "Grid view" }).click();
      } else {
        // The retained To Read page was mounted at /, but its navigation link uses the alias.
        await expect(page.locator(".book-card")).toHaveCount(100);
        await page.getByRole("link", { name: "Finished", exact: true }).click();
        await page.getByRole("link", { name: "To Read", exact: true }).click();
        await expect(page).toHaveURL(/\/shelves\/to-read$/);
      }
      await page
        .locator(mode === "list" ? ".book-title-link" : ".grid-cover-link")
        .first()
        .click();

      await expect(
        page.getByRole("heading", { name: "Navigation book 001" }),
      ).toBeVisible();
      await expect(page.locator(".book-author")).toHaveText(
        "by Navigation author",
      );
      await expect(page.getByText("Loading book...")).toHaveCount(0);
      const thumbnail = page.locator(
        '.book-detail img[src$="/preview-thumbnail.svg"]',
      );
      const cover = page.locator('.book-detail img[src$="/preview-cover.svg"]');
      await expect(thumbnail).toBeVisible();
      await expect
        .poll(() =>
          thumbnail.evaluate(
            (element) => (element as HTMLImageElement).naturalWidth,
          ),
        )
        .toBe(300);
      await expect(cover).toBeHidden();

      // Exercise both request orderings: metadata before the cover, and the cover before metadata.
      if (mode === "list") {
        finishBook();
        await expect(
          page.getByRole("heading", { name: "Refreshed book" }),
        ).toBeVisible();
        await expect(thumbnail).toBeVisible();
      }
      const previewBounds = await page
        .locator(".book-cover-section")
        .boundingBox();
      finishCover();
      await expect(cover).toBeVisible();
      expect(await page.locator(".book-cover-section").boundingBox()).toEqual(
        previewBounds,
      );
      await expect(thumbnail).toBeHidden();
      finishBook();
      await expect(
        page.getByRole("heading", { name: "Refreshed book" }),
      ).toBeVisible();
      await expect(cover).toBeVisible();
      await expect(thumbnail).toBeHidden();
      expect(await page.locator(".book-cover-section").boundingBox()).toEqual(
        previewBounds,
      );
    } finally {
      finishBook();
      finishCover();
      finishEvents();
    }
  });
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
