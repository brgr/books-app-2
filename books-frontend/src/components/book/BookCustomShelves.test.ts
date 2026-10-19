import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { isRef, ref } from "vue";
import BookCustomShelves from "./BookCustomShelves.vue";

const { addBookToShelf, removeBookFromShelf, shelfChanged } = vi.hoisted(() => ({
  addBookToShelf: vi.fn(),
  removeBookFromShelf: vi.fn(),
  shelfChanged: vi.fn(),
}));

vi.mock("../../api/books", () => ({
  addBookToShelf,
  removeBookFromShelf,
  getShelves: vi.fn(),
  getBookShelves: vi.fn(),
}));
vi.mock("../../cache/invalidate", () => ({ invalidateCache: { shelfChanged } }));

const shelves = ref([
  { ref: "custom:1", display_name: "A long custom shelf name", name: "A long custom shelf name" },
  { ref: "custom:2", display_name: "Another shelf", name: "Another shelf" },
]);
const bookShelves = ref([shelves.value[0]]);
vi.mock("../../composables/useCachedQuery", () => ({
  useCachedQuery: (key: string | (() => string)) => ({
    data: isRef(key) ? bookShelves : shelves,
    error: ref(null),
    refresh: vi.fn(),
  }),
}));

describe("BookCustomShelves editor", () => {
  beforeEach(() => {
    bookShelves.value = [shelves.value[0]];
    vi.clearAllMocks();
  });
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("opens with focus in the dialog and restores focus when closed", async () => {
    const wrapper = mount(BookCustomShelves, {
      props: { bookId: 42 },
      attachTo: document.body,
      global: { stubs: { RouterLink: true } },
    });
    const open = wrapper.get("button").element;
    await wrapper.get("button").trigger("click");
    expect(document.activeElement).toBe(document.querySelector(".modal-header button"));
    expect(document.querySelectorAll(".shelf-option")).toHaveLength(2);
    expect(document.querySelector(".shelf-options")?.getAttribute("role")).toBe("group");

    (document.querySelector(".modal-header button") as HTMLButtonElement).click();
    await flushPromises();
    expect(document.querySelector(".modal")).toBeNull();
    expect(document.activeElement).toBe(open);
    wrapper.unmount();
  });

  it("toggles a shelf immediately without closing the editor", async () => {
    const wrapper = mount(BookCustomShelves, {
      props: { bookId: 42 },
      attachTo: document.body,
      global: { stubs: { RouterLink: true } },
    });
    await wrapper.get("button").trigger("click");
    const checkboxes = document.querySelectorAll<HTMLInputElement>(".shelf-option input");
    expect(checkboxes[0]?.checked).toBe(true);
    expect(checkboxes[1]?.checked).toBe(false);
    checkboxes[1]?.click();
    await flushPromises();
    expect(addBookToShelf).toHaveBeenCalledWith("custom:2", 42);
    expect(shelfChanged).toHaveBeenCalledWith(42);
    expect(document.querySelector(".modal")).not.toBeNull();
    wrapper.unmount();
  });
});
