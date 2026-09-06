import { describe, it, expect, beforeEach } from "vitest";
import { ref, nextTick } from "vue";
import { usePaginatedList, type PageResult } from "./usePaginatedList";
import { cacheClear, cacheGet } from "../cache/store";

async function flush(times = 20) {
  for (let i = 0; i < times; i++) {
    await nextTick();
    await new Promise((r) => setTimeout(r, 5));
  }
}

describe("usePaginatedList", () => {
  beforeEach(async () => {
    await cacheClear();
  });

  it("refreshes shifted pages and discards a page requested before the reorder", async () => {
    let order = ["A", "B", "C", "D", "E", "F"];
    let stalePage: ((page: PageResult<string>) => void) | undefined;
    let delayPage = true;
    const list = usePaginatedList<string>({
      resourceId: 1,
      cacheKey: (id, page) => `shelf:${id}:page=${page}`,
      cacheKeyPrefix: (id) => `shelf:${id}:`,
      fetchPage: async (_, page) => {
        if (page === 2 && delayPage) {
          return new Promise<PageResult<string>>((resolve) => {
            stalePage = resolve;
          });
        }
        return { items: order.slice((page - 1) * 2, page * 2), page, pages: 3 };
      },
      itemKey: (item) => item,
    });
    await flush();

    list.loadMore();
    await flush();

    order = ["B", "C", "D", "E", "F", "A"];
    delayPage = false;
    await list.refreshLoaded();
    stalePage!({ items: ["C", "D"], page: 2, pages: 3 });
    await flush();

    expect(list.items.value).toEqual(["B", "C", "D", "E"]);
    expect(await cacheGet("shelf:1:page=2")).toBeUndefined();

    list.loadMore();
    await flush();

    expect(list.items.value).toEqual(order);
    expect(list.hasMore.value).toBe(false);
  });

  it("updates items in-memory and invalidates the resource's cached pages on `replaceItems`", async () => {
    const resourceId = ref<number | null>(1);
    const { items, replaceItems } = usePaginatedList<string>({
      resourceId,
      cacheKey: (id, page) => `shelf:${id}:page=${page}`,
      cacheKeyPrefix: (id) => `shelf:${id}:`,
      fetchPage: async () => ({ items: ["A", "B"], page: 1, pages: 1 }),
      itemKey: (x) => x,
    });

    await flush();
    expect(items.value).toEqual(["A", "B"]);
    expect(await cacheGet<{ items: string[] }>("shelf:1:page=1")).toBeDefined();

    // Reorder items via replaceItems
    await replaceItems(["B", "A"]);
    await nextTick();

    // In-memory reflects the reorder immediately
    expect(items.value).toEqual(["B", "A"]);
    // And the now-stale cached page has been invalidated, so a remount refetches instead of serving old order.
    expect(await cacheGet<{ items: string[] }>("shelf:1:page=1")).toBeUndefined();
  });
});
