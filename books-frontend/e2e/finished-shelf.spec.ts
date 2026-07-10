import { execFileSync } from "node:child_process";
import { type BrowserContext, expect, test } from "@playwright/test";

/**
 * Finished shelf shows 'No finished books yet' even though there are finished books
 */

const FINISHED_BOOK_TITLE = process.env.FINISHED_BOOK_TITLE ?? "UNIX and Linux System Administration Handbook, 5/e";

// Get a real access token for the seeded dev user by asking the backend to sign one, then authenticate the browser via
// the HttpOnly-style cookie
function getDevToken(): string {
  const out = execFileSync(
    "uv",
    ["run", "python", "-c", "from app.auth.security import create_access_token; print(create_access_token('dev'))"],
    { cwd: "../books-backend", encoding: "utf8" },
  );

  return out.trim().split("\n").pop()!;
}

async function authenticate(context: BrowserContext) {
  const token = getDevToken();
  await context.addCookies([{ name: "access_token", value: token, domain: "localhost", path: "/" }]);
}

test("finished book is visible on the Finished shelf", async ({ context, page }) => {
  await authenticate(context);

  await page.goto("/");

  // The default "To Read" shelf must be fully loaded first, so booksData holds a multi-page result and the
  // infinite-scroll sentinel is live (hasMore === true). This mirrors the real user flow: browse To Read, then tap
  // Finished.
  await expect(page.locator(".book-card, .grid-cover, .books-list > *").first()).toBeVisible();
  await page.waitForLoadState("networkidle");

  // Switch to the "Finished" shelf.
  await page.getByText("Finished", { exact: true }).first().click();

  // The finished book must appear on the Finished shelf.
  await expect(page.getByText(FINISHED_BOOK_TITLE, { exact: false }).first()).toBeVisible();

  // ...and the empty state must NOT be shown.
  await expect(page.getByText("No finished books yet.")).toHaveCount(0);
});
