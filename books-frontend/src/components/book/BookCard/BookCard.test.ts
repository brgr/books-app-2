import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { h } from "vue";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";
import type { Book } from "../../../api/types";
import { takeBookPreview } from "../../../router/bookPreview";
import BookCard from "./BookCard.vue";

enableAutoUnmount(afterEach);

const book = { id: 1, title: "Selected book", user_book: null } as Book;

async function mountCard() {
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { render: () => h(BookCard, { book }) } },
      {
        path: "/books/:id",
        name: "book-detail",
        component: {
          setup() {
            const preview = takeBookPreview(1);
            return () => h("h1", preview?.title ?? "No preview");
          },
        },
      },
    ],
  });
  await router.push("/");
  const wrapper = mount(RouterView, { global: { plugins: [router] } });
  return { wrapper, router };
}

describe("BookCard navigation", () => {
  it.each([".book-title-link", ".book-cover-link"])("hands off the book when %s is followed", async (selector) => {
    const { wrapper, router } = await mountCard();
    await wrapper.get(selector).trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/books/1?from=/");
    expect(wrapper.get("h1").text()).toBe("Selected book");
    expect(takeBookPreview(1)).toBeNull();
  });

  it.each(["ctrlKey", "metaKey", "shiftKey", "altKey"])("keeps %s clicks as ordinary browser links", async (key) => {
    const { wrapper, router } = await mountCard();
    const link = wrapper.get(".book-title-link");
    expect(link.attributes("href")).toBe("/books/1?from=/");
    await link.trigger("click", { [key]: true });
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/");
    expect(takeBookPreview(1)).toBeNull();
  });
});
