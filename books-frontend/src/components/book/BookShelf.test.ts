import { describe, it, expect } from "vitest";
import { mount } from "@vue/test-utils";
import BookShelf from "./BookShelf.vue";
import BookCard from "./BookCard/BookCard.vue";
import BookCoverTile from "./BookCoverTile.vue";
import type { Book } from "../../api/types";

function makeBook(overrides: Partial<Book> = {}): Book {
  return {
    id: 1,
    title: "Dune",
    author: "Frank Herbert",
    isbn: null,
    description: null,
    published_date: null,
    page_count: null,
    cover_image_url: null,
    cover_thumbnail_url: null,
    created_at: "",
    updated_at: "",
    user_status: null,
    ...overrides,
  };
}

const books = [makeBook(), makeBook({ id: 2, title: "Europe", author: "Tim Flannery" })];

// BookCard links to the detail route, which needs a router the shelf itself never touches
function mountShelf(props: { viewMode: "list" | "grid"; title?: string | null; showProgress?: boolean }) {
  return mount(BookShelf, {
    props: { books, ...props },
    global: { stubs: { RouterLink: true } },
  });
}

describe("BookShelf", () => {
  it("renders a card per book in list view", () => {
    const wrapper = mountShelf({ viewMode: "list" });
    expect(wrapper.findAllComponents(BookCard)).toHaveLength(2);
    expect(wrapper.find(".books-list").exists()).toBe(true);
    expect(wrapper.find(".books-grid").exists()).toBe(false);
  });

  it("renders a cover tile per book in grid view", () => {
    const wrapper = mountShelf({ viewMode: "grid" });
    expect(wrapper.findAllComponents(BookCoverTile)).toHaveLength(2);
    expect(wrapper.find(".books-grid").exists()).toBe(true);
    expect(wrapper.find(".books-list").exists()).toBe(false);
  });

  it("shows the heading only when a title is given", () => {
    expect(mountShelf({ viewMode: "list", title: "Reading now" }).find("h2").text()).toBe("Reading now");
    expect(mountShelf({ viewMode: "list" }).find("h2").exists()).toBe(false);
  });

  it("passes showProgress down to its tiles", () => {
    const wrapper = mountShelf({ viewMode: "grid", showProgress: true });
    expect(wrapper.findComponent(BookCoverTile).props("showProgress")).toBe(true);
  });

  it("re-emits a tile selection as select", async () => {
    const wrapper = mountShelf({ viewMode: "grid" });
    wrapper.findComponent(BookCoverTile).vm.$emit("click", 2);
    expect(wrapper.emitted("select")).toEqual([[2]]);
  });

  it("re-emits a card menu request", async () => {
    const wrapper = mountShelf({ viewMode: "list" });
    const payload = { bookId: 2, x: 10, y: 20 };
    wrapper.findComponent(BookCard).vm.$emit("menu", payload);
    expect(wrapper.emitted("menu")).toEqual([[payload]]);
  });
});
