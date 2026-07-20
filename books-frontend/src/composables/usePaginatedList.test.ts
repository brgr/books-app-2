import { describe, it, expect, beforeEach } from "vitest";
import { ref, nextTick } from "vue";
import { usePaginatedList } from "./usePaginatedList";
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
