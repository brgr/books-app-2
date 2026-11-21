import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount, type VueWrapper } from "@vue/test-utils";
import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";
import BookEditView from "./BookEditView.vue";
import { getBook, searchGoogleBooks, updateBook } from "../api/books";
import { uploadBookCover } from "../api/covers";
import CoverEditField from "../components/bookForm/cover/CoverEditField.vue";
import { getPendingCover, stagePendingCover } from "../components/bookForm/cover/pendingCoverUploads";
import { invalidateAfter } from "../query/invalidate";
import { makeBook } from "../test/factories";

vi.mock("../api/books", () => ({
  getBook: vi.fn(),
  updateBook: vi.fn(),
  deleteBook: vi.fn(),
  searchGoogleBooks: vi.fn(),
}));
vi.mock("../api/covers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/covers")>()),
  uploadBookCover: vi.fn(),
}));
vi.mock("../query/invalidate", () => ({ invalidateAfter: { bookUpdated: vi.fn(), bookDeleted: vi.fn() } }));

const book = makeBook({
  id: 42,
  published_date: "1965-08-01T00:00:00",
  page_count: 0,
  cover_image_url: "/uploads/original.jpg",
});

async function mountEditView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "books", component: { template: "<div />" } },
      { path: "/books/:id/edit", name: "book-edit", component: BookEditView },
      { path: "/books/:id", name: "book-detail", component: { template: "<div>Book details</div>" } },
    ],
  });
  await router.push("/books/42/edit");

  const wrapper = mount(RouterView, {
    global: {
      plugins: [router, [VueQueryPlugin, { queryClient: new QueryClient() }]],
      stubs: { NavigationBar: true, CoverModal: true },
    },
  });
  await vi.waitFor(() => expect(wrapper.find("form").exists()).toBe(true));
  return { wrapper, router };
}

function findButton(wrapper: VueWrapper, text: string) {
  const button = wrapper.findAll("button").find((candidate) => candidate.text() === text);
  if (!button) {
    throw new Error(`No button "${text}"`);
  }
  return button;
}

function stageCover() {
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = vi.fn(() => "blob:edited-cover");
      static revokeObjectURL = vi.fn();
    },
  );
  const file = new File(["cover"], "cover.png", { type: "image/png" });
  return { file, url: stagePendingCover(file) };
}

enableAutoUnmount(afterEach);

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(getBook).mockResolvedValue({ ...book });
  vi.mocked(updateBook).mockResolvedValue({ ...book });
  vi.mocked(uploadBookCover).mockResolvedValue({ ...book, cover_image_url: "/uploads/edited-cover.png" });
  vi.spyOn(console, "error").mockImplementation(() => {});
});

afterEach(() => {
  vi.restoreAllMocks();
  vi.unstubAllGlobals();
});

describe("editing a book", () => {
  it("saves edited metadata, invalidates the cache, and opens book details", async () => {
    const { wrapper, router } = await mountEditView();

    await wrapper.get('[name="title"]').setValue("  Edited title  ");
    await wrapper.get('[name="author"]').setValue("  An Author  ");
    await wrapper.get('[name="isbn"]').setValue(" 1234567890 ");
    await wrapper.get('[name="google_books_id"]').setValue(" dune-volume ");
    await wrapper.get('[name="description"]').setValue("  Edited description  ");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(updateBook).toHaveBeenCalledExactlyOnceWith(42, {
      title: "Edited title",
      author: "An Author",
      isbn: "1234567890",
      google_books_id: "dune-volume",
      page_count: 0,
      published_date: "1965-08-01",
      description: "Edited description",
      cover_image_url: "/uploads/original.jpg",
    });
    expect(uploadBookCover).not.toHaveBeenCalled();
    expect(invalidateAfter.bookUpdated).toHaveBeenCalledWith(42);
    expect(router.currentRoute.value.name).toBe("book-detail");
  });

  it("keeps only the id when a Google Books link is pasted into the Google Books ID field", async () => {
    const { wrapper } = await mountEditView();
    const input = wrapper.get('[name="google_books_id"]');

    await input.setValue("https://books.google.de/books?id=LTpjQwAACAAJ&hl=de");

    expect((input.element as HTMLInputElement).value).toBe("LTpjQwAACAAJ");
  });

  it("finds a Google Books id by title and author and saves the chosen one", async () => {
    vi.mocked(searchGoogleBooks).mockResolvedValue([
      {
        title: "Dune",
        author: "Frank Herbert",
        isbn: null,
        description: null,
        published_date: "1965",
        page_count: null,
        thumbnail: null,
        image_url: null,
        google_books_id: "dune-volume",
      },
    ]);
    const { wrapper } = await mountEditView();

    await findButton(wrapper, "Find on Google Books").trigger("click");
    await flushPromises();
    expect(searchGoogleBooks).toHaveBeenCalledWith("Dune Frank Herbert");

    await findButton(wrapper, "Use").trigger("click");
    expect((wrapper.get('[name="google_books_id"]').element as HTMLInputElement).value).toBe("dune-volume");
    expect(wrapper.find('[aria-label="Google Books matches"]').exists()).toBe(false);

    await wrapper.get("form").trigger("submit");
    await flushPromises();
    expect(updateBook).toHaveBeenCalledExactlyOnceWith(42, expect.objectContaining({ google_books_id: "dune-volume" }));
  });

  it("retains a staged cover after an upload failure and retries it before saving metadata", async () => {
    vi.mocked(uploadBookCover).mockRejectedValueOnce(new Error("Upload failed"));
    const { wrapper, router } = await mountEditView();
    const { file, url } = stageCover();
    wrapper.getComponent(CoverEditField).vm.$emit("update:modelValue", url);
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toBe("Failed to save book. Please try again.");
    expect(getPendingCover(url)).toBe(file);
    expect(updateBook).not.toHaveBeenCalled();
    expect(invalidateAfter.bookUpdated).not.toHaveBeenCalled();

    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(uploadBookCover).toHaveBeenNthCalledWith(1, 42, file);
    expect(uploadBookCover).toHaveBeenNthCalledWith(2, 42, file);
    expect(updateBook).toHaveBeenCalledExactlyOnceWith(42, expect.objectContaining({ cover_image_url: undefined }));
    expect(getPendingCover(url)).toBeUndefined();
    expect(invalidateAfter.bookUpdated).toHaveBeenCalledWith(42);
    expect(router.currentRoute.value.name).toBe("book-detail");
  });

  it("keeps a successfully uploaded cover when metadata saving fails, without uploading it again on retry", async () => {
    vi.mocked(updateBook).mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: "Could not save metadata" } },
    });
    const { wrapper, router } = await mountEditView();
    const { file, url } = stageCover();
    wrapper.getComponent(CoverEditField).vm.$emit("update:modelValue", url);
    await wrapper.get('[name="title"]').setValue("Edited title");
    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toBe("Could not save metadata");
    expect(getPendingCover(url)).toBeUndefined();

    await wrapper.get("form").trigger("submit");
    await flushPromises();

    expect(uploadBookCover).toHaveBeenCalledExactlyOnceWith(42, file);
    expect(updateBook).toHaveBeenCalledTimes(2);
    expect(updateBook).toHaveBeenLastCalledWith(
      42,
      expect.objectContaining({ title: "Edited title", cover_image_url: "/uploads/edited-cover.png" }),
    );
    expect(router.currentRoute.value.name).toBe("book-detail");
  });
});
