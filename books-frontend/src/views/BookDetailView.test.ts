import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import BookDetailView from "./BookDetailView.vue";
import { clearRating, getBook, getBookEvents, setRating } from "../api/books";
import { type Book, BookEventType, ReadingShelf, type UserBook } from "../api/types";
import { cacheClear, cacheGet, cacheSet } from "../cache/store";
import { cacheKeys } from "../cache/keys";

vi.mock("vue-router", () => ({
  useRoute: () => ({ params: { id: "1" } }),
  useRouter: () => ({ push: vi.fn() }),
}));
vi.mock("../api/books", () => ({
  getBook: vi.fn(),
  getBookEvents: vi.fn(),
  setRating: vi.fn(),
  clearRating: vi.fn(),
  setShelf: vi.fn(),
  addBookProgress: vi.fn(),
  createBook: vi.fn(),
}));

const userBook: UserBook = {
  id: 1,
  user_id: 1,
  book_id: 1,
  shelf: ReadingShelf.FINISHED,
  started_at: { value: "2026-09-01T00:00:00+02:00", precision: "day" },
  finished_at: { value: "2026-09-05T00:00:00+02:00", precision: "day" },
  notes: null,
  current_page: null,
  current_percent: null,
  rating: 3.5,
  created_at: "",
  updated_at: "",
};
const book: Book = {
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
  user_book: userBook,
};

async function renderBook() {
  const wrapper = mount(BookDetailView, {
    global: {
      stubs: {
        NavigationBar: true,
        BookShelfButton: true,
        BookReadingCard: true,
        BookNotes: true,
        BookCustomShelves: true,
        BookMetadata: true,
        BookSearchModal: true,
      },
    },
  });
  await vi.waitFor(() => expect(wrapper.find("select").exists()).toBe(true));
  return wrapper;
}

describe("book ratings", () => {
  beforeEach(async () => {
    vi.resetAllMocks();
    await cacheClear();
    vi.mocked(getBook).mockResolvedValue(book);
    vi.mocked(getBookEvents).mockResolvedValue([]);
  });

  it("saves a half-star rating and refreshes cached shelves and activity", async () => {
    const shelfKey = cacheKeys.shelfBooks("reading:finished", 1, 20);
    await cacheSet(shelfKey, { items: [book] });
    const wrapper = await renderBook();
    expect(wrapper.get("select").element.value).toBe("3.5");
    vi.mocked(setRating).mockResolvedValue({ ...userBook, rating: 4.5 });
    vi.mocked(getBookEvents).mockResolvedValue([
      {
        id: "rating",
        event_type: BookEventType.RATING_SET,
        rating: 4.5,
        occurred_at: "2026-09-05T12:00:00Z",
      },
    ]);

    await wrapper.get("select").setValue("4.5");
    await vi.waitFor(() => expect(wrapper.text()).toContain("Rated 4.5 / 5 stars"));
    expect(setRating).toHaveBeenCalledWith(1, 4.5);
    expect((await cacheGet<Book>(cacheKeys.book(1)))?.data.user_book?.rating).toBe(4.5);
    expect(await cacheGet(shelfKey)).toBeUndefined();
    wrapper.unmount();
  });

  it("clears a rating and displays the clear event", async () => {
    const wrapper = await renderBook();
    vi.mocked(clearRating).mockResolvedValue(undefined);
    vi.mocked(getBookEvents).mockResolvedValue([
      {
        id: "clear",
        event_type: BookEventType.RATING_SET,
        rating: null,
        occurred_at: "2026-09-05T12:00:00Z",
      },
    ]);

    await wrapper.get("select").setValue("");

    await vi.waitFor(() => expect(wrapper.text()).toContain("Rating cleared"));
    expect(clearRating).toHaveBeenCalledWith(1);
    expect(setRating).not.toHaveBeenCalled();
    expect((await cacheGet<Book>(cacheKeys.book(1)))?.data.user_book?.rating).toBeNull();
    expect(wrapper.find('[role="alert"]').exists()).toBe(false);
    expect((await cacheGet<Book>(cacheKeys.book(1)))?.data.user_book?.finished_at).toEqual(userBook.finished_at);
    wrapper.unmount();
  });

  it("disables the selector while saving and preserves the saved rating on failure", async () => {
    const wrapper = await renderBook();
    let reject!: (error: Error) => void;
    vi.mocked(setRating).mockReturnValue(
      new Promise((_, rejectPromise) => {
        reject = rejectPromise;
      }),
    );

    const log = vi.spyOn(console, "error").mockImplementation(() => {});
    await wrapper.get("select").setValue("5");

    expect(wrapper.get("select").element.disabled).toBe(true);

    reject(new Error("Network error"));
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toContain("Failed to save rating");
    expect(wrapper.get("select").element.disabled).toBe(false);
    expect(wrapper.get("select").element.value).toBe("3.5");

    log.mockRestore();
    wrapper.unmount();
  });

  it("hides rating controls for books outside the library", async () => {
    vi.mocked(getBook).mockResolvedValue({ ...book, user_book: null });
    const wrapper = mount(BookDetailView, {
      global: {
        stubs: {
          NavigationBar: true,
          BookShelfButton: true,
          BookNotes: true,
          BookCustomShelves: true,
          BookMetadata: true,
        },
      },
    });

    await vi.waitFor(() => expect(wrapper.text()).toContain("Dune"));
    expect(wrapper.find("select").exists()).toBe(false);

    wrapper.unmount();
  });
});
