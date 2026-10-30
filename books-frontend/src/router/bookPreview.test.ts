import { describe, expect, it } from "vitest";
import type { Book } from "../api/types";
import { navigateWithBookPreview, takeBookPreview } from "./bookPreview";

const book = { id: 1, title: "Selected book" } as Book;

describe("book preview handoff", () => {
  it("gives the selected book to the detail view once", async () => {
    await navigateWithBookPreview(book, async () => {
      expect(takeBookPreview(1)).toBe(book);
      expect(takeBookPreview(1)).toBeNull();
    });
  });

  it("does not give another book's preview to the detail view", async () => {
    await navigateWithBookPreview(book, async () => {
      expect(takeBookPreview(2)).toBeNull();
      expect(takeBookPreview(1)).toBeNull();
    });
  });

  it("releases unused previews when navigation finishes or is cancelled", async () => {
    await navigateWithBookPreview(book, async () => {});
    expect(takeBookPreview(1)).toBeNull();
  });

  it("releases the preview when navigation fails", async () => {
    const error = new Error("Navigation failed");
    await expect(
      navigateWithBookPreview(book, async () => {
        throw error;
      }),
    ).rejects.toThrow(error);
    expect(takeBookPreview(1)).toBeNull();
  });
});
