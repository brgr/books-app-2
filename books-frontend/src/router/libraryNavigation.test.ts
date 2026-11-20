import { afterEach, describe, expect, it, vi } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import { createLibraryNavigation, libraryOrigin, libraryPageKey } from "./libraryNavigation";

function testRouter() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "books", component: {} },
      { path: "/shelves/:shelf", name: "shelf", component: {} },
      { path: "/shelves/custom/:id", name: "custom-shelf", component: {} },
      { path: "/books/:id", name: "book-detail", component: {} },
      { path: "/books/:id/edit", name: "book-edit", component: {} },
      { path: "/login", name: "login", component: {} },
    ],
  });
  const navigation = createLibraryNavigation();
  navigation.install(router);
  return { router, navigation };
}

describe("library navigation", () => {
  afterEach(() => vi.restoreAllMocks());

  it("shares root and To Read state, while keeping other shelves separate", () => {
    const { router } = testRouter();
    expect(libraryPageKey(router.resolve("/"))).toBe(libraryPageKey(router.resolve("/shelves/to-read")));
    expect(libraryPageKey(router.resolve("/shelves/finished"))).toBe("/shelves/finished");
    expect(libraryPageKey(router.resolve("/shelves/custom/12"))).toBe("/shelves/custom/12");
    expect(libraryPageKey(router.resolve("/books/1"))).toBeNull();
  });

  it("only permits local library destinations for the detail back link", () => {
    const { router } = testRouter();
    expect(libraryOrigin(router, "/shelves/custom/12")).toBe("/shelves/custom/12");
    for (const value of [
      undefined,
      ["/shelves/finished"],
      "https://example.com",
      "//example.com",
      "/books/1",
      "/login",
    ]) {
      expect(libraryOrigin(router, value)).toBe("/");
    }
  });

  it("carries the originating shelf through detail, edit and save navigation", async () => {
    const { router } = testRouter();
    await router.push("/shelves/custom/12");
    await router.push("/books/1");
    expect(router.currentRoute.value.query.from).toBe("/shelves/custom/12");
    await router.push("/books/1/edit");
    expect(router.currentRoute.value.query.from).toBe("/shelves/custom/12");
    await router.push("/books/1");
    expect(router.currentRoute.value.query.from).toBe("/shelves/custom/12");
  });

  it("restores tab and history positions, and clears them on logout", async () => {
    const { router, navigation } = testRouter();
    const scroller = document.createElement("div");
    scroller.className = "page-scroller";
    scroller.scrollTo = vi.fn() as typeof scroller.scrollTo;
    document.body.append(scroller);
    const scrollTo = vi.mocked(scroller.scrollTo);

    await router.push("/shelves/to-read");
    const tab = router.currentRoute.value;
    scroller.scrollTop = 4321;
    await router.push("/books/1");
    const detail = router.currentRoute.value;
    scroller.scrollTop = 123;
    await router.push("/shelves/finished");

    // A visit to the tab returns to its last position
    await navigation.scrollBehavior(tab, detail, null);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 4321 });

    // Back and Forward return to the history entry's position
    await navigation.scrollBehavior(detail, tab, { left: 0, top: 0 });
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 123 });

    await router.push("/login");
    await navigation.scrollBehavior(tab, detail, null);
    expect(scrollTo).toHaveBeenLastCalledWith({ top: 0 });

    scroller.remove();
  });
});
