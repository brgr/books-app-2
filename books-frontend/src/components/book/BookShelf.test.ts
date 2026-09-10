import { describe, it, expect, beforeEach, vi } from "vitest";
import { mount } from "@vue/test-utils";
import { defineComponent, h, nextTick, ref } from "vue";
import BookShelf from "./BookShelf.vue";
import BookCard from "./BookCard/BookCard.vue";
import BookCoverTile from "./BookCoverTile.vue";
import BookContextMenu from "./BookContextMenu.vue";
import { reorderShelfItem } from "../../api/books";
import { type Book, type PaginatedBooks } from "../../api/types";
import { cacheClear } from "../../cache/store";
import { provideLibraryPage } from "../../composables/useLibraryPage";

const push = vi.fn();
vi.mock("vue-router", () => ({
  useRouter: () => ({ push, resolve: ({ params }: { params: { id: number } }) => ({ href: `/books/${params.id}` }) }),
}));

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
  return { items, total: items.length, page: 1, page_size: 100, pages: 1 };
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
      provideLibraryPage({ searchQuery: ref("") });
      return () => h(BookShelf, { shelf: "reading:started", ...props });
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
    vi.mocked(reorderShelfItem).mockReset();
    vi.mocked(reorderShelfItem).mockResolvedValue();
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
    expect(localStorage.getItem("shelfViewMode:reading:started")).toBe("grid");
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

  it.each([
    { view: "list", edge: "top", bookId: 2, hasMore: false, expected: [2, 1] },
    { view: "grid", edge: "top", bookId: 2, hasMore: false, expected: [2, 1] },
    { view: "list", edge: "bottom", bookId: 1, hasMore: false, expected: [2, 1] },
    { view: "grid", edge: "bottom", bookId: 1, hasMore: false, expected: [2, 1] },
    { view: "list", edge: "bottom", bookId: 1, hasMore: true, expected: [2] },
  ] as const)(
    "moves to $edge immediately in $view view (more pages: $hasMore)",
    async ({ view, edge, bookId, hasMore, expected }) => {
      getShelfBooks.mockResolvedValue({ ...page(books), pages: hasMore ? 2 : 1 });
      const wrapper = mountShelf({ defaultViewMode: view });
      await flush();

      let finishSave!: () => void;
      vi.mocked(reorderShelfItem).mockImplementationOnce(() => new Promise<void>((resolve) => (finishSave = resolve)));
      let finishRefresh!: (result: PaginatedBooks) => void;
      getShelfBooks.mockImplementationOnce(() => new Promise<PaginatedBooks>((resolve) => (finishRefresh = resolve)));
      const renderedIds = () =>
        (view === "list" ? wrapper.findAllComponents(BookCard) : wrapper.findAllComponents(BookCoverTile)).map(
          (book) => book.props().book.id,
        );

      const book = view === "list" ? wrapper.findComponent(BookCard) : wrapper.findComponent(BookCoverTile);
      book.vm.$emit("menu", { bookId, x: 10, y: 20 });
      await nextTick();
      wrapper.findComponent(BookContextMenu).vm.$emit("move", edge);
      await nextTick();

      expect(renderedIds()).toEqual(expected);
      expect(reorderShelfItem).toHaveBeenCalledWith("reading:started", { moved_book_id: bookId, edge });
      expect(wrapper.findComponent(BookContextMenu).exists()).toBe(false);

      finishSave();
      await flush();
      expect(renderedIds()).toEqual(expected);

      const refreshedBooks = hasMore ? [books[1]!, makeBook({ id: 3 })] : [books[1]!, books[0]!];
      finishRefresh({ ...page(refreshedBooks), pages: hasMore ? 2 : 1 });
      await flush();
      expect(renderedIds()).toEqual(refreshedBooks.map((book) => book.id));
      expect(wrapper.find('[role="status"]').text()).toBe(`Moved to ${edge}.`);
      wrapper.unmount();
    },
  );

  it("restores the original order when saving fails even if refreshing also fails", async () => {
    const wrapper = mountShelf();
    await flush();
    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    let failSave!: (error: Error) => void;
    vi.mocked(reorderShelfItem).mockImplementationOnce(() => new Promise<void>((_, reject) => (failSave = reject)));
    getShelfBooks.mockRejectedValueOnce(new Error("Offline"));

    wrapper.findComponent(BookCard).vm.$emit("menu", { bookId: 2, x: 10, y: 20 });
    await nextTick();
    wrapper.findComponent(BookContextMenu).vm.$emit("move", "top");
    await nextTick();
    expect(wrapper.findAllComponents(BookCard).map((book) => book.props("book").id)).toEqual([2, 1]);

    failSave(new Error("Offline"));
    await flush();
    expect(wrapper.findAllComponents(BookCard).map((book) => book.props("book").id)).toEqual([1, 2]);
    expect(wrapper.find('[role="alert"]').text()).toContain("Could not refresh the shelf");
    expect(wrapper.find('[role="status"]').exists()).toBe(false);
    log.mockRestore();
    wrapper.unmount();
  });
});
