import { afterEach, describe, expect, it } from "vitest";
import { enableAutoUnmount, flushPromises, mount } from "@vue/test-utils";
import { QueryClient, VueQueryPlugin } from "@tanstack/vue-query";
import { h } from "vue";
import { createMemoryHistory, createRouter, RouterView } from "vue-router";
import { type Book } from "../../../api/types";
import { queryKeys } from "../../../query/keys";
import { makeBook } from "../../../test/factories";
import BookCard from "./BookCard.vue";

enableAutoUnmount(afterEach);

const book = makeBook({ title: "Selected book" });

async function mountCard() {
  const queryClient = new QueryClient();
  const seeded = () => queryClient.getQueryData<Book>(queryKeys.book.detail(1));
  const router = createRouter({
    history: createMemoryHistory(),
    routes: [
      { path: "/", component: { render: () => h(BookCard, { book }) } },
      {
        path: "/books/:id",
        name: "book-detail",
        component: { render: () => h("h1", seeded()?.title ?? "Nothing seeded") },
      },
    ],
  });
  await router.push("/");
  const wrapper = mount(RouterView, { global: { plugins: [router, [VueQueryPlugin, { queryClient }]] } });
  return { wrapper, router, seeded };
}

describe("BookCard navigation", () => {
  it.each([".book-title-link", ".book-cover-link"])("hands off the book when %s is followed", async (selector) => {
    const { wrapper, router } = await mountCard();
    await wrapper.get(selector).trigger("click");
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/books/1?from=/");
    expect(wrapper.get("h1").text()).toBe("Selected book");
  });

  it.each(["ctrlKey", "metaKey", "shiftKey", "altKey"])("keeps %s clicks as ordinary browser links", async (key) => {
    const { wrapper, router, seeded } = await mountCard();
    const link = wrapper.get(".book-title-link");
    expect(link.attributes("href")).toBe("/books/1?from=/");
    await link.trigger("click", { [key]: true });
    await flushPromises();

    expect(router.currentRoute.value.fullPath).toBe("/");
    expect(seeded()).toBeUndefined();
  });
});
