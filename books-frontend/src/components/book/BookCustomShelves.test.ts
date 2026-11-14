import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { mount, flushPromises } from "@vue/test-utils";
import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import BookCustomShelves from "./BookCustomShelves.vue";

const { addBookToShelf, removeBookFromShelf, getShelves, getBookShelves, shelfChanged } = vi.hoisted(() => ({
  addBookToShelf: vi.fn(),
  removeBookFromShelf: vi.fn(),
  getShelves: vi.fn(),
  getBookShelves: vi.fn(),
  shelfChanged: vi.fn(),
}));

vi.mock("../../api/books", () => ({
  addBookToShelf,
  removeBookFromShelf,
  getShelves,
  getBookShelves,
}));
vi.mock("../../query/invalidate", () => ({ invalidateAfter: { shelfChanged } }));

const shelves = [
  { ref: "custom:1", display_name: "A long custom shelf name", name: "A long custom shelf name" },
  { ref: "custom:2", display_name: "Another shelf", name: "Another shelf" },
];

async function mountShelves() {
  const wrapper = mount(BookCustomShelves, {
    props: { bookId: 42 },
    attachTo: document.body,
    global: { stubs: { RouterLink: true }, plugins: [[VueQueryPlugin, { queryClient: new QueryClient() }]] },
  });
  await flushPromises();

  return wrapper;
}

describe("BookCustomShelves editor", () => {
  beforeEach(() => {
    vi.clearAllMocks();
    getShelves.mockResolvedValue(shelves);
    getBookShelves.mockResolvedValue([shelves[0]]);
  });
  afterEach(() => {
    document.body.innerHTML = "";
  });

  it("opens with focus in the dialog and restores focus when closed", async () => {
    const wrapper = await mountShelves();
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
    const wrapper = await mountShelves();
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
