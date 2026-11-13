import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookCoverTile from "./BookCoverTile.vue";
import { ReadingShelf } from "../../api/types";
import { makeBook, makeUserBook } from "../../test/factories";

describe("BookCoverTile", () => {
  it("renders cover image when thumbnail url is present", () => {
    const wrapper = mount(BookCoverTile, {
      props: { href: "/books/1", book: makeBook({ cover_thumbnail_url: "/media/x.jpg" }) },
    });
    const img = wrapper.find("img.grid-cover");
    expect(img.exists()).toBe(true);
    expect(img.attributes("alt")).toBe("Dune");
  });

  it("falls back to cover_image_url when thumbnail missing", () => {
    const wrapper = mount(BookCoverTile, {
      props: { href: "/books/1", book: makeBook({ cover_image_url: "/media/full.jpg" }) },
    });
    expect(wrapper.find("img.grid-cover").exists()).toBe(true);
  });

  it("renders placeholder with title when no cover urls", () => {
    const wrapper = mount(BookCoverTile, { props: { href: "/books/1", book: makeBook() } });
    expect(wrapper.find("img.grid-cover").exists()).toBe(false);
    const placeholder = wrapper.find(".grid-cover-placeholder");
    expect(placeholder.exists()).toBe(true);
    expect(placeholder.text()).toContain("Dune");
  });

  it('emits "click" with book id when tile is clicked', async () => {
    const wrapper = mount(BookCoverTile, { props: { href: "/books/1", book: makeBook({ id: 42 }) } });
    await wrapper.find("a.grid-cover-link").trigger("click");
    expect(wrapper.emitted("click")?.[0]?.[0]).toBe(42);
  });

  it("does not show progress badge by default", () => {
    const wrapper = mount(BookCoverTile, {
      props: {
        href: "/books/1",
        book: makeBook({
          page_count: 200,
          user_book: makeUserBook({
            shelf: ReadingShelf.STARTED,
            current_page: 50,
          }),
        }),
      },
    });
    expect(wrapper.find(".grid-progress-badge").exists()).toBe(false);
  });

  it("shows progress badge when showProgress prop is true and book is STARTED with page data", () => {
    const wrapper = mount(BookCoverTile, {
      props: {
        href: "/books/1",
        showProgress: true,
        book: makeBook({
          page_count: 200,
          user_book: makeUserBook({
            shelf: ReadingShelf.STARTED,
            current_page: 50,
          }),
        }),
      },
    });
    const badge = wrapper.find(".grid-progress-badge");
    expect(badge.exists()).toBe(true);
    expect(badge.text()).toContain("25%");
  });

  it("hides progress badge when showProgress=true but shelf is not STARTED", () => {
    const wrapper = mount(BookCoverTile, {
      props: {
        href: "/books/1",
        showProgress: true,
        book: makeBook({
          page_count: 200,
          user_book: makeUserBook({
            shelf: ReadingShelf.WANT_TO_READ,
            current_page: 50,
          }),
        }),
      },
    });
    expect(wrapper.find(".grid-progress-badge").exists()).toBe(false);
  });
});
