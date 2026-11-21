import { AxiosError } from "axios";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";
import BookAddView from "./BookAddView.vue";
import { createBook, searchGoogleBooks } from "../api/books";
import { uploadBookCover } from "../api/covers";
import CoverEditField from "../components/book/cover/CoverEditField.vue";
import { getPendingCover, stagePendingCover } from "../components/book/cover/pendingCoverUploads";
import { invalidateAfter } from "../query/invalidate";

vi.mock("../api/books", () => ({ createBook: vi.fn(), searchGoogleBooks: vi.fn() }));
vi.mock("../api/covers", async (importOriginal) => ({
  ...(await importOriginal<typeof import("../api/covers")>()),
  uploadBookCover: vi.fn(),
}));
vi.mock("../query/invalidate", () => ({ invalidateAfter: { bookAdded: vi.fn(), bookUpdated: vi.fn() } }));

async function mountAddView() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "books", component: { template: "<div />" } },
      { path: "/books/add", name: "book-add", component: BookAddView },
      { path: "/books/:id", name: "book-detail", component: { template: "<div>Book details</div>" } },
      { path: "/other", name: "other", component: { template: "<div>Other page</div>" } },
    ],
  });

  await router.push("/books/add");

  const wrapper = mount(RouterView, {
    global: { plugins: [router], stubs: { NavigationBar: true, CoverModal: true } },
  });
  return { wrapper, router };
}

async function searchForBook() {
  const { wrapper, router } = await mountAddView();
  await wrapper.get("input").setValue("Dune");
  await wrapper.get(".search-input-group").trigger("submit");
  await flushPromises();

  return { wrapper, router };
}

async function enterBookManually() {
  const view = await mountAddView();
  await view.wrapper.get("#book-add-manual-tab").trigger("click");
  await view.wrapper.get('[name="title"]').setValue("  A Manual Book  ");
  await view.wrapper.get('[name="author"]').setValue("  An Author  ");
  return view;
}

function stageCover() {
  vi.stubGlobal(
    "URL",
    class extends URL {
      static createObjectURL = vi.fn(() => "blob:manual-cover");
      static revokeObjectURL = vi.fn();
    },
  );
  const file = new File(["cover"], "cover.png", { type: "image/png" });
  return { file, url: stagePendingCover(file) };
}

enableAutoUnmount(afterEach);

beforeEach(() => {
  vi.resetAllMocks();
  vi.mocked(createBook).mockResolvedValue({ id: 42 } as Awaited<ReturnType<typeof createBook>>);
  vi.mocked(uploadBookCover).mockResolvedValue({
    id: 42,
    cover_image_url: "/uploads/manual-cover.png",
  } as Awaited<ReturnType<typeof uploadBookCover>>);
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

afterEach(() => vi.unstubAllGlobals());

describe("adding a book", () => {
  it("shows an upstream search failure without saying no books were found", async () => {
    const unavailable = Object.assign(new AxiosError("upstream unavailable"), {
      response: { data: { detail: "Google Books is temporarily unavailable. Please try again." } },
    });
    vi.mocked(searchGoogleBooks).mockResolvedValueOnce([]).mockRejectedValueOnce(unavailable);
    const { wrapper } = await searchForBook();
    expect(wrapper.text()).toContain("No books found.");

    await wrapper.get(".search-input-group").trigger("submit");
    await flushPromises();

    expect(wrapper.get('[role="alert"]').text()).toBe("Google Books is temporarily unavailable. Please try again.");
    expect(wrapper.text()).not.toContain("No books found.");
  });

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

    expect(router.currentRoute.value.name).toBe("book-add");
    expect(invalidateAfter.bookAdded).not.toHaveBeenCalled();

    finishSave();

    await flushPromises();

    expect(createBook).toHaveBeenCalledExactlyOnceWith(
      expect.objectContaining({
        title: "Dune",
        author: "Frank Herbert",
        isbn: "123",
        google_books_id: "dune",
        page_count: 412,
        description: undefined,
        published_date: undefined,
        cover_image_url: "https://example.com/cover.jpg",
      }),
    );
    expect(invalidateAfter.bookAdded).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.name).toBe("books");
  });

  it("does not redirect after leaving while the selection is being saved", async () => {
    let finishPendingStep!: () => void;
    vi.mocked(createBook).mockImplementation(
      () =>
        new Promise((resolve) => {
          finishPendingStep = () => resolve({} as Awaited<ReturnType<typeof createBook>>);
        }),
    );

    const { wrapper, router } = await searchForBook();
    await wrapper.get(".btn-select").trigger("click");
    await flushPromises();

    expect(createBook).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.name).toBe("book-add");

    await wrapper.get(".page-header a").trigger("click");
    await flushPromises();
    expect(router.currentRoute.value.name).toBe("books");
    expect(wrapper.findComponent(BookAddView).exists()).toBe(false);

    await router.push({ name: "other" });
    finishPendingStep();
    await flushPromises();

    expect(invalidateAfter.bookAdded).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.name).toBe("other");
  });

  it("creates a book with only title and author, then opens its details after invalidating the library", async () => {
    const { wrapper, router } = await enterBookManually();
    await wrapper.get("#book-add-manual-panel form").trigger("submit");
    await wrapper.get("#book-add-manual-panel form").trigger("submit");
    await flushPromises();

    expect(createBook).toHaveBeenCalledExactlyOnceWith({
      title: "A Manual Book",
      author: "An Author",
      isbn: undefined,
      google_books_id: null,
      page_count: undefined,
      published_date: undefined,
      description: undefined,
      cover_image_url: undefined,
    });
    expect(invalidateAfter.bookAdded).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.name).toBe("book-detail");
    expect(router.currentRoute.value.params.id).toBe("42");
  });

  it("requires a nonblank title when adding manually", async () => {
    const { wrapper } = await mountAddView();
    await wrapper.get("#book-add-manual-tab").trigger("click");
    await wrapper.get('[name="title"]').setValue("   ");
    await wrapper.get("#book-add-manual-panel form").trigger("submit");

    expect(wrapper.get('[role="alert"]').text()).toBe("Please enter a title.");
    expect(createBook).not.toHaveBeenCalled();
  });

  it.each(["retry", "continue"])(
    "can %s after a cover upload fails without creating a duplicate book",
    async (action) => {
      vi.mocked(uploadBookCover).mockRejectedValueOnce(new Error("Upload failed"));
      const { wrapper, router } = await enterBookManually();
      const { file, url } = stageCover();
      wrapper.getComponent(CoverEditField).vm.$emit("update:modelValue", url);
      await wrapper.get("#book-add-manual-panel form").trigger("submit");
      await flushPromises();

      expect(wrapper.get('#book-add-manual-panel [role="alert"]').text()).toContain("Your book was added");
      expect(getPendingCover(url)).toBe(file);
      expect(invalidateAfter.bookAdded).toHaveBeenCalledOnce();
      expect(router.currentRoute.value.name).toBe("book-add");
      if (action === "retry") {
        await wrapper.get("#book-add-manual-panel form").trigger("submit");
      } else {
        await wrapper.get(".form-actions .text-link").trigger("click");
      }
      await flushPromises();

      expect(createBook).toHaveBeenCalledOnce();
      expect(uploadBookCover).toHaveBeenCalledTimes(action === "retry" ? 2 : 1);
      expect(getPendingCover(url)).toBeUndefined();
      expect(router.currentRoute.value.name).toBe("book-detail");
    },
  );

  it("uploads the submitted manual cover after navigating away during book creation", async () => {
    let finishCreation!: () => void;
    vi.mocked(createBook).mockImplementationOnce(async () => {
      await new Promise<void>((resolve) => {
        finishCreation = resolve;
      });
      return { id: 42 } as Awaited<ReturnType<typeof createBook>>;
    });

    const { wrapper, router } = await enterBookManually();
    const { file, url } = stageCover();
    wrapper.getComponent(CoverEditField).vm.$emit("update:modelValue", url);
    await wrapper.get("#book-add-manual-panel form").trigger("submit");
    await flushPromises();
    expect(createBook).toHaveBeenCalledOnce();
    expect(uploadBookCover).not.toHaveBeenCalled();

    await router.push({ name: "other" });
    expect(wrapper.findComponent(CoverEditField).exists()).toBe(false);
    expect(getPendingCover(url)).toBeUndefined();

    finishCreation();
    await flushPromises();

    expect(uploadBookCover).toHaveBeenCalledExactlyOnceWith(42, file);
    expect(invalidateAfter.bookAdded).toHaveBeenCalledOnce();
    expect(invalidateAfter.bookUpdated).toHaveBeenCalledExactlyOnceWith(42);
    expect(router.currentRoute.value.name).toBe("other");
  });

  it("does not redirect after leaving while a manual cover upload is pending", async () => {
    let finishUpload!: () => void;
    vi.mocked(uploadBookCover).mockImplementationOnce(async () => {
      await new Promise<void>((resolve) => {
        finishUpload = resolve;
      });
      return { id: 42, cover_image_url: "/uploads/cover.png" } as Awaited<ReturnType<typeof uploadBookCover>>;
    });
    const { wrapper, router } = await enterBookManually();
    const { url } = stageCover();
    wrapper.getComponent(CoverEditField).vm.$emit("update:modelValue", url);
    await wrapper.get("#book-add-manual-panel form").trigger("submit");
    await flushPromises();
    expect(uploadBookCover).toHaveBeenCalledOnce();

    await router.push({ name: "other" });
    finishUpload();
    await flushPromises();

    expect(createBook).toHaveBeenCalledOnce();
    expect(invalidateAfter.bookAdded).toHaveBeenCalledOnce();
    expect(router.currentRoute.value.name).toBe("other");
  });
});
