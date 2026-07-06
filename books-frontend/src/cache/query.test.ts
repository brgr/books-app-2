import { describe, it, expect, beforeEach, vi } from "vitest";
import { cachedQuery } from "./query";
import { cacheSet, cacheClear, cacheGet } from "./store";

describe("cachedQuery", () => {
  beforeEach(async () => {
    await cacheClear();
  });

  it("fetches and caches when cache is empty", async () => {
    const onData = vi.fn();
    const fetcher = vi.fn().mockResolvedValue("network-data");

    await cachedQuery({ key: "k", fetcher, onData });

    expect(fetcher).toHaveBeenCalledOnce();
    expect(onData).toHaveBeenCalledWith("network-data", "network");
    const cached = await cacheGet<string>("k");
    expect(cached!.data).toBe("network-data");
  });

  it("returns cached data first, then network data", async () => {
    await cacheSet("k", "cached-data");

    const calls: Array<[unknown, string]> = [];
    const onData = vi.fn((data, source) => calls.push([data, source]));
    const fetcher = vi.fn().mockResolvedValue("fresh-data");

    await cachedQuery({ key: "k", fetcher, onData });

    expect(calls).toEqual([
      ["cached-data", "cache"],
      ["fresh-data", "network"],
    ]);
  });

  it("returns cached data and fires onError when fetcher throws", async () => {
    await cacheSet("k", "cached-data");

    const onData = vi.fn();
    const onError = vi.fn();
    const fetcher = vi.fn().mockRejectedValue(new Error("network failure"));

    await cachedQuery({ key: "k", fetcher, onData, onError });

    expect(onData).toHaveBeenCalledWith("cached-data", "cache");
    expect(onData).toHaveBeenCalledTimes(1);
    expect(onError).toHaveBeenCalledWith(expect.any(Error));
  });

  it("fires onError with no data when cache is empty and fetcher throws", async () => {
    const onData = vi.fn();
    const onError = vi.fn();
    const fetcher = vi.fn().mockRejectedValue(new Error("fail"));

    await cachedQuery({ key: "k", fetcher, onData, onError });

    expect(onData).not.toHaveBeenCalled();
    expect(onError).toHaveBeenCalledWith(expect.any(Error));
  });

  it("does not write to the cache when the call was superseded before resolving", async () => {
    // Reproduces the shelf-switch bug: opening "Finished" sometimes showed no books even though there were some.
    //
    // A cachedQuery call has two inputs that should describe the same thing:
    //   - `key`   : a fixed string, e.g. "lists:1:books:page=1", decided up front
    //   - fetcher : reads activeListId/page LIVE each time it is called
    // The call does `await cacheGet(key)` and only THEN calls the fetcher. That await is a pause during which other
    // code can run.
    //
    // Timeline:
    //   1. On "To Read" (list 1), a call starts with key "lists:1:books:page=1" and pauses at `await cacheGet(...)`.
    //   2. During the pause the user taps "Finished", which sets the shared activeListId ref to 2.
    //   3. The call resumes and runs the fetcher, which now reads list 2 and returns Finished's books.
    //   4. cacheSet writes those Finished books under the OLD key ("...list 1").
    //
    // So the cache entry for one list now holds another list's data. The mirror of this (a stale Finished call resuming
    // after you left) writes empty/wrong data under the Finished key, and because the cache is persistent (IndexedDB)
    // it stays wrong across reloads.
    //
    // The fix: a call that has been superseded (isCurrent() === false) must not write to the cache at all.
    const onData = vi.fn();
    const fetcher = vi.fn().mockResolvedValue("finished-data");

    await cachedQuery({
      key: "lists:1:books:page=1", // "To Read" list key
      fetcher,
      onData,
      isCurrent: () => false, // superseded (user switched shelves)
    });

    expect(await cacheGet("lists:1:books:page=1")).toBeUndefined();
    expect(onData).not.toHaveBeenCalledWith("finished-data", "network");
  });

  it("does not emit network data or error when superseded", async () => {
    const onData = vi.fn();
    const onError = vi.fn();
    const fetcher = vi.fn().mockRejectedValue(new Error("late failure"));

    await cachedQuery({ key: "k", fetcher, onData, onError, isCurrent: () => false });

    expect(onError).not.toHaveBeenCalled();
  });

  it("commits when the call remains current", async () => {
    const onData = vi.fn();
    const fetcher = vi.fn().mockResolvedValue("fresh");

    await cachedQuery({ key: "k", fetcher, onData, isCurrent: () => true });

    expect(onData).toHaveBeenCalledWith("fresh", "network");
    expect((await cacheGet<string>("k"))!.data).toBe("fresh");
  });
});
