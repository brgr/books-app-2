import { describe, it, expect, beforeEach, vi } from "vitest";
import { ref, nextTick } from "vue";
import { useCachedQuery } from "./useCachedQuery";
import { cacheSet, cacheGet, cacheClear } from "../cache/store";

async function flushPromises() {
  for (let i = 0; i < 5; i++) {
    await new Promise<void>((r) => setTimeout(r, 0));
  }
}

describe("useCachedQuery", () => {
  beforeEach(async () => {
    await cacheClear();
  });

  it("fetches from network when cache is empty", async () => {
    const fetcher = vi.fn().mockResolvedValue("fresh");

    const { data } = useCachedQuery("key", fetcher);

    expect(data.value).toBeNull();

    await flushPromises();

    expect(data.value).toBe("fresh");
  });

  it("serves cached data first, then updates with network data", async () => {
    await cacheSet("key", "cached");
    const fetcher = vi.fn().mockResolvedValue("fresh");

    const { data, isStale } = useCachedQuery("key", fetcher);

    await flushPromises();

    expect(data.value).toBe("fresh");
    expect(isStale.value).toBe(false);
  });

  it("sets isStale to true when showing cached data", async () => {
    await cacheSet("key", "cached");
    let resolveFetch: (v: string) => void;
    const fetcher = vi.fn().mockReturnValue(
      new Promise<string>((r) => {
        resolveFetch = r;
      }),
    );

    const { data, isStale } = useCachedQuery("key", fetcher);

    await flushPromises();

    expect(data.value).toBe("cached");
    expect(isStale.value).toBe(true);

    resolveFetch!("fresh");
    await flushPromises();

    expect(data.value).toBe("fresh");
    expect(isStale.value).toBe(false);
  });

  it("sets error when fetcher fails and cache is empty", async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error("fail"));

    const { data, error } = useCachedQuery("key", fetcher);

    await flushPromises();

    expect(data.value).toBeNull();
    expect(error.value).toBeInstanceOf(Error);
  });

  it("keeps cached data when fetcher fails", async () => {
    await cacheSet("key", "cached");
    const fetcher = vi.fn().mockRejectedValue(new Error("fail"));

    const { data, error } = useCachedQuery("key", fetcher);

    await flushPromises();

    expect(data.value).toBe("cached");
    expect(error.value).toBeInstanceOf(Error);
  });

  it("refresh re-fetches data", async () => {
    const fetcher = vi.fn().mockResolvedValue("v1");

    const { data, refresh } = useCachedQuery("key", fetcher);
    await flushPromises();
    expect(data.value).toBe("v1");

    fetcher.mockResolvedValue("v2");
    await refresh();

    expect(data.value).toBe("v2");
  });

  it("invalidate clears cache and re-fetches", async () => {
    await cacheSet("key", "old-cached");
    const fetcher = vi.fn().mockResolvedValue("new");

    const { data, invalidate } = useCachedQuery("key", fetcher);
    await flushPromises();

    await invalidate();

    expect(data.value).toBe("new");
  });

  it("setData updates the value and mirrors it into the cache", async () => {
    const fetcher = vi.fn().mockResolvedValue("v1");

    const { data, setData } = useCachedQuery("key", fetcher);
    await flushPromises();
    expect(data.value).toBe("v1");

    // Optimistically replace the value (e.g. after a persisted mutation)
    await setData("v2");

    // In-memory reflects it immediately, and the cache entry is rewritten so a remount serves the new value
    expect(data.value).toBe("v2");
    expect((await cacheGet<string>("key"))?.data).toBe("v2");
  });

  it("reacts to key changes", async () => {
    const key = ref("books:1");
    const fetcher = vi.fn().mockImplementation(async () => `data-for-${key.value}`);

    const { data } = useCachedQuery(key, fetcher);
    await flushPromises();
    expect(data.value).toBe("data-for-books:1");

    key.value = "books:2";
    await nextTick();
    await flushPromises();

    expect(data.value).toBe("data-for-books:2");
  });

  it("does not overwrite a saved mutation with an older background response", async () => {
    // We "store" the promise's resolve function in the "finish" variable. Like this, we can later
    // finish (resolve) the promise and like that finish the mocked server response.
    let finish!: (value: string) => void;
    const fetcher = vi.fn(() => new Promise<string>((resolve) => (finish = resolve)));
    
    const { data, setData } = useCachedQuery("key", fetcher, { initialData: () => "shelf preview" });
    await flushPromises();
    
    await setData("saved value");
    finish("older server value");
    await flushPromises();
    
    expect(data.value).toBe("saved value");
    expect((await cacheGet<string>("key"))?.data).toBe("saved value");
  });

  it("clears the previous resource immediately and ignores its delayed response after a key change", async () => {
    const key = ref("books:1");
    let finishFirst!: (value: string) => void;
    const fetcher = vi
      .fn()
      .mockImplementationOnce(() => new Promise<string>((resolve) => (finishFirst = resolve)))
      .mockImplementation(() => new Promise<string>(() => {}));
    const { data, isStale } = useCachedQuery(key, fetcher, {
      initialData: () => (key.value === "books:1" ? "shelf preview" : null),
    });
    
    expect(data.value).toBe("shelf preview");
    expect(isStale.value).toBe(true);
    await flushPromises();

    key.value = "books:2";
    await nextTick();
    expect(data.value).toBeNull();
    finishFirst("wrong book");
    await flushPromises();
    
    expect(data.value).toBeNull();
    expect(await cacheGet("books:1")).toBeUndefined();
  });

  it("does not fetch when enabled is false", async () => {
    const fetcher = vi.fn().mockResolvedValue("data");
    const enabled = ref(false);

    const { data } = useCachedQuery("key", fetcher, { enabled });
    await flushPromises();

    expect(fetcher).not.toHaveBeenCalled();
    expect(data.value).toBeNull();

    enabled.value = true;
    await nextTick();
    await flushPromises();

    expect(fetcher).toHaveBeenCalledOnce();
    expect(data.value).toBe("data");
  });
});
