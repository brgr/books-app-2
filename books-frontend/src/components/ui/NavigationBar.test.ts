import { flushPromises, mount } from "@vue/test-utils";
import { describe, expect, it } from "vitest";
import { createMemoryHistory, createRouter } from "vue-router";
import NavigationBar from "./NavigationBar.vue";

async function mountNavigation(path: string) {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", name: "books" },
      { path: "/shelves/:shelf", name: "shelf" },
      { path: "/shelves", name: "custom-shelves" },
      { path: "/shelves/custom/:id", name: "custom-shelf" },
      { path: "/books/:id", name: "book-detail" },
      { path: "/books/:id/edit", name: "book-edit" },
      { path: "/settings", name: "settings" },
    ].map((route) => ({ ...route, component: { template: "<div />" } })),
  });

  await router.push(path);
  await router.isReady();

  return { router, wrapper: mount(NavigationBar, { global: { plugins: [router] } }) };
}

describe("library navigation", () => {
  it("navigates from the bar without page-provided slots or handlers", async () => {
    const { router, wrapper } = await mountNavigation("/");
    const nav = wrapper.get('nav[aria-label="Library"]');

    expect(nav.get('[aria-current="page"]').text()).toBe("To Read");

    for (const [path, label] of [
      ["/shelves/finished", "Finished"],
      ["/shelves", "Shelves"],
      ["/shelves/to-read", "To Read"],
    ]) {
      await nav.get(`a[href="${path}"]`).trigger("click");
      await flushPromises();

      expect(router.currentRoute.value.path).toBe(path);
      expect(nav.get('[aria-current="page"]').text()).toBe(label);
    }

    wrapper.unmount();
  });

  it("tracks direct route changes and preserves library-only visibility", async () => {
    const { router, wrapper } = await mountNavigation("/shelves/custom/12");

    for (const path of ["/shelves/custom/12", "/shelves/abandoned", "/shelves"]) {
      await router.push(path);
      await flushPromises();

      expect(wrapper.get('nav[aria-label="Library"] .active').text()).toBe("Shelves");
    }

    for (const path of ["/settings", "/books/12", "/books/12/edit"]) {
      await router.push(path);
      await flushPromises();

      expect(wrapper.find('nav[aria-label="Library"]').exists()).toBe(false);
    }

    wrapper.unmount();
  });
});
