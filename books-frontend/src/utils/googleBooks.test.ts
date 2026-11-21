import { describe, expect, it } from "vitest";
import { googleBooksIdFromUrl } from "./googleBooks";

describe("googleBooksIdFromUrl", () => {
  it.each([
    "https://books.google.com/books?id=LTpjQwAACAAJ",
    "https://books.google.de/books?id=LTpjQwAACAAJ&hl=de",
    "https://books.google.com/books/about/Unterwegs.html?id=LTpjQwAACAAJ&redir_esc=y",
    "https://www.google.com/books/edition/Unterwegs/LTpjQwAACAAJ?hl=en",
    "https://www.google.co.uk/books/edition/_/LTpjQwAACAAJ",
    "https://play.google.com/store/books/details?id=LTpjQwAACAAJ",
    "  https://books.google.com/books?id=LTpjQwAACAAJ  ",
  ])("reads the id from %s", (url) => {
    expect(googleBooksIdFromUrl(url)).toBe("LTpjQwAACAAJ");
  });

  it.each([
    "LTpjQwAACAAJ",
    "https://example.com/books?id=LTpjQwAACAAJ",
    "https://books.google.com.example.com/books?id=LTpjQwAACAAJ",
    "https://play.google.com/store/apps/details?id=com.example.app",
    "https://books.google.com/books",
  ])("returns null for %s", (text) => {
    expect(googleBooksIdFromUrl(text)).toBeNull();
  });
});
