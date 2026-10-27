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

  it("restores tab positions, honors browser history, and clears positions on logout", async () => {
    const { router, navigation } = testRouter();
    await router.push("/shelves/to-read");
    const tab = router.currentRoute.value;
    vi.spyOn(window, "scrollY", "get").mockReturnValue(4321);
    await router.push("/books/1");
    const detail = router.currentRoute.value;
    expect(await navigation.scrollBehavior(tab, detail, null)).toEqual({ left: 0, top: 4321 });
    expect(await navigation.scrollBehavior(tab, detail, { left: 0, top: 123 })).toEqual({ left: 0, top: 123 });
    await router.push("/login");
    expect(await navigation.scrollBehavior(tab, detail, null)).toEqual({ left: 0, top: 0 });
  });
});
