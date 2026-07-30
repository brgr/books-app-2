import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, h, nextTick, ref } from "vue";
import BookShelf from "./BookShelf.vue";
import BookCard from "./BookCard/BookCard.vue";
import BookCoverTile from "./BookCoverTile.vue";
import { ShelfName, type Book, type PaginatedBooks } from "../../api/types";
import { cacheClear } from "../../cache/store";
import { provideLibraryPage } from "../../composables/useLibraryPage";

const push = vi.fn();
vi.mock("vue-router", () => ({ useRouter: () => ({ push }) }));

const getShelfBooks = vi.fn();
vi.mock("../../api/books", () => ({
  getShelfBooks: (...args: unknown[]) => getShelfBooks(...args),
  reorderShelfItem: vi.fn(async () => ({})),
}));

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
    user_book: null,
    ...overrides,
  };
}

const books = [makeBook(), makeBook({ id: 2, title: "Europe", author: "Tim Flannery" })];

function page(items: Book[]): PaginatedBooks {
  return { items, total: items.length, page: 1, page_size: 30, pages: 1 };
}

async function flush(times = 20) {
  for (let i = 0; i < times; i++) {
    await nextTick();
    await new Promise((r) => setTimeout(r, 5));
  }
}

/**
 * A shelf only works inside a library page, so tests mount it under a host providing that context.
 */
function mountShelf(props: { title?: string | null; showProgress?: boolean; defaultViewMode?: "list" | "grid" } = {}) {
  const Host = defineComponent({
    setup() {
      provideLibraryPage({
        searchQuery: ref(""),
        shelves: ref([{ id: 7, name: ShelfName.STARTED, display_name: "Reading" }]),
      });
      return () => h(BookShelf, { shelf: ShelfName.STARTED, ...props });
    },
  });

  // BookCard links to the detail route, which needs a router the shelf itself never touches
  return mount(Host, { global: { stubs: { RouterLink: true } } });
}

describe("BookShelf", () => {
  beforeEach(async () => {
    await cacheClear();
    localStorage.clear();
    push.mockClear();
    getShelfBooks.mockReset();
    getShelfBooks.mockResolvedValue(page(books));
  });

  it("renders a card per book in list view", async () => {
    const wrapper = mountShelf();
    await flush();

    expect(wrapper.findAllComponents(BookCard)).toHaveLength(2);
    expect(wrapper.find(".books-list").exists()).toBe(true);
    expect(wrapper.find(".books-grid").exists()).toBe(false);
  });

  it("renders a cover tile per book in grid view", async () => {
    const wrapper = mountShelf({ defaultViewMode: "grid" });
    await flush();

    expect(wrapper.findAllComponents(BookCoverTile)).toHaveLength(2);
    expect(wrapper.find(".books-grid").exists()).toBe(true);
    expect(wrapper.find(".books-list").exists()).toBe(false);
  });

  it("shows the heading only when a title is given", async () => {
    const titled = mountShelf({ title: "Reading now" });
    const untitled = mountShelf();
    await flush();

    expect(titled.find("h2").text()).toBe("Reading now");
    expect(untitled.find("h2").exists()).toBe(false);
  });

  it("switches layout when the toggle is clicked, and remembers the reader's choice", async () => {
    const wrapper = mountShelf();
    await flush();

    await wrapper.find('.view-btn[title="Grid view"]').trigger("click");

    expect(wrapper.find(".books-grid").exists()).toBe(true);
    expect(localStorage.getItem(`shelfViewMode:${ShelfName.STARTED}`)).toBe("grid");
  });

  it("passes showProgress down to its tiles", async () => {
    const wrapper = mountShelf({ defaultViewMode: "grid", showProgress: true });
    await flush();

    expect(wrapper.findComponent(BookCoverTile).props("showProgress")).toBe(true);
  });

  it("opens a book when its cover is tapped", async () => {
    const wrapper = mountShelf({ defaultViewMode: "grid" });
    await flush();

    wrapper.findComponent(BookCoverTile).vm.$emit("click", 2);

    expect(push).toHaveBeenCalledWith({ name: "book-detail", params: { id: 2 } });
  });

  it("renders nothing at all for an empty shelf, so the page keeps no space for it", async () => {
    getShelfBooks.mockResolvedValue(page([]));
    const wrapper = mountShelf({ title: "Reading now" });
    await flush();

    // BookCardShelf also carries a .book-shelf class, so this pins the shelf's own root element
    expect(wrapper.find("section.book-shelf").exists()).toBe(false);
  });

  it("opens the context menu where a book reports a long press", async () => {
    const wrapper = mountShelf();
    await flush();

    wrapper.findComponent(BookCard).vm.$emit("menu", { bookId: 2, x: 10, y: 20 });
    await nextTick();

    expect(wrapper.findComponent({ name: "BookContextMenu" }).exists()).toBe(true);
  });
});
