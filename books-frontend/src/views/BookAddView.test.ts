import { beforeEach, describe, expect, it, vi } from "vitest";
import { flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter } from "vue-router";
import BookAddView from "./BookAddView.vue";
import { createBook, searchGoogleBooks } from "../api/books";
import { invalidateCache } from "../cache/invalidate";

vi.mock("../api/books", () => ({ createBook: vi.fn(), searchGoogleBooks: vi.fn() }));
vi.mock("../cache/invalidate", () => ({ invalidateCache: { bookAdded: vi.fn() } }));

async function searchForBook() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "books", component: { template: "<div />" } },
      { path: "/books/add", name: "book-add", component: BookAddView },
    ],
  });

  await router.push("/books/add");

  const wrapper = mount(BookAddView, { global: { plugins: [router], stubs: { NavigationBar: true } } });
  await wrapper.get("input").setValue("Dune");
  await wrapper.get("form").trigger("submit");
  await flushPromises();

  return { wrapper, router };
}

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(searchGoogleBooks).mockResolvedValue([
    {
      google_books_id: "dune",
      title: "Dune",
      author: "Frank Herbert",
      isbn: "123",
      thumbnail: "https://example.com/cover.jpg",
      page_count: 412,
      description: null,
      published_date: null,
    },
  ]);
});

describe("adding a book", () => {
  it("searches, saves the selection, and invalidates shelves before returning to the library", async () => {
    let finishSave!: () => void;
    vi.mocked(createBook).mockImplementation(
      () =>
        new Promise((resolve) => {
          finishSave = () => resolve({} as Awaited<ReturnType<typeof createBook>>);
        }),
    );

    const { wrapper, router } = await searchForBook();

    expect(searchGoogleBooks).toHaveBeenCalledWith("Dune");

    await wrapper.get(".btn-select").trigger("click");

    expect(wrapper.get(".btn-select").attributes("disabled")).toBeDefined();
    expect(router.currentRoute.value.name).toBe("book-add");
    expect(invalidateCache.bookAdded).not.toHaveBeenCalled();

    finishSave();

    await flushPromises();

    expect(createBook).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({
        title: "Dune",
        author: "Frank Herbert",
        isbn: "123",
        page_count: 412,
        description: undefined,
        published_date: undefined,
        cover_image_url: "https://example.com/cover.jpg",
      }),
    );
    expect(invalidateCache.bookAdded).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.name).toBe("books");

    wrapper.unmount();
  });

  it("keeps results available for retry when saving fails", async () => {
    vi.mocked(createBook).mockRejectedValueOnce({ response: { data: { detail: "Could not save book" } } });
    const { wrapper, router } = await searchForBook();
    await wrapper.get(".btn-select").trigger("click");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toBe("Could not save book");
    expect(router.currentRoute.value.name).toBe("book-add");
    expect(invalidateCache.bookAdded).not.toHaveBeenCalled();
    expect(wrapper.get(".btn-select").attributes("disabled")).toBeUndefined();

    await wrapper.get(".btn-select").trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.name).toBe("books");

    wrapper.unmount();
  });
});
