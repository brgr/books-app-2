import { describe, expect, it } from "vitest";
import { mount } from "@vue/test-utils";
import type { Book } from "../../api/types";
import BookMetadata from "./BookMetadata.vue";

const book: Book = {
  id: 1,
  title: "Dune",
  author: "Frank Herbert",
  isbn: "9780441172719",
  google_books_id: null,
  description: null,
  published_date: null,
  page_count: null,
  cover_image_url: null,
  cover_thumbnail_url: null,
  created_at: "2026-10-18T12:00:00Z",
  updated_at: "2026-10-18T12:00:00Z",
  user_book: null,
};

describe("Amazon.it link", () => {
  it.each([
    { name: "ISBN (with formatting)", overrides: { isbn: "978-0-441-17271-9" }, query: "9780441172719" },
    {
      name: "title and author with special characters",
      overrides: { isbn: null, title: "L'été & Books?", author: "A. B. + C." },
      query: "L'été & Books? A. B. + C.",
    },
    { name: "title only", overrides: { isbn: null, author: null }, query: "Dune" },
  ])("searches by $name in a new tab", ({ overrides, query }) => {
    const wrapper = mount(BookMetadata, { props: { book: { ...book, ...overrides } } });
    const link = wrapper.get("a[href^='https://www.amazon.it/']");
    const url = new URL(link.attributes("href")!);

    expect(url.origin).toBe("https://www.amazon.it");
    expect(url.pathname).toBe("/s");
    expect(Object.fromEntries(url.searchParams)).toEqual({ k: query });
    expect(link.text()).toBe("Search on Amazon.it");
    expect(link.attributes("target")).toBe("_blank");
    expect(link.attributes("rel")?.split(" ")).toEqual(expect.arrayContaining(["noopener", "noreferrer"]));
  });
});

describe("Google Books link", () => {
  it.each([
    {
      name: "exact entry even when an ISBN is available",
      overrides: { google_books_id: "volume&other=value" },
      label: "View on Google Books",
      params: { id: "volume&other=value" },
    },
    {
      name: "ISBN search for a book without a Google Books ID",
      overrides: { isbn: "978-0-441-17271-9" },
      label: "Search on Google Books",
      params: { q: "isbn:9780441172719" },
    },
    {
      name: "title and author search with special characters",
      overrides: { isbn: null, title: "L'été & Books?", author: "A. B. + C." },
      label: "Search on Google Books",
      params: { q: "L'été & Books? A. B. + C." },
    },
    {
      name: "title search when ISBN and author are missing",
      overrides: { isbn: null, author: null },
      label: "Search on Google Books",
      params: { q: "Dune" },
    },
  ])("opens the $name in a new tab", ({ overrides, label, params }) => {
    const wrapper = mount(BookMetadata, { props: { book: { ...book, ...overrides } } });
    const link = wrapper.get("a");
    const url = new URL(link.element.href);

    expect(url.origin).toBe("https://books.google.com");
    expect(url.pathname).toBe("/books");
    expect(Object.fromEntries(url.searchParams)).toEqual(params);
    expect(link.text()).toBe(label);
    expect(link.attributes("target")).toBe("_blank");
    expect(link.element.rel.split(" ")).toEqual(expect.arrayContaining(["noopener", "noreferrer"]));
  });

  it("uses a search link for an older cached book without the ID field", () => {
    const legacyBook: Partial<Book> = { ...book };
    delete legacyBook.google_books_id;
    const wrapper = mount(BookMetadata, { props: { book: legacyBook as Book } });
    const link = wrapper.get("a");

    expect(link.text()).toBe("Search on Google Books");
    expect(new URL(link.element.href).searchParams.get("q")).toBe("isbn:9780441172719");
  });
});
