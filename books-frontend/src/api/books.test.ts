import { afterEach, describe, expect, it } from "vitest";
import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios";
import { apiClient } from "./client";
import { addBookProgress, getShelfBooks, reorderShelfItem } from "./books";
import type { BookProgressUpdate } from "./types";

const originalAdapter = apiClient.defaults.adapter;

function captureRequest(): Promise<InternalAxiosRequestConfig> {
  return new Promise((resolve) => {
    apiClient.defaults.adapter = (async (config) => {
      resolve(config);
      return {
        data: { items: [], total: 0, page: 1, page_size: 20, pages: 0 },
        status: 200,
        statusText: "OK",
        headers: {},
        config,
      };
    }) as AxiosAdapter;
  });
}

describe("shelf API uses tagged refs", () => {
  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter;
  });

  it("uses a tagged ref when loading a reading shelf", async () => {
    const request = captureRequest();

    await getShelfBooks("reading:started");

    await expect(request).resolves.toMatchObject({ url: "/shelves/reading:started/books" });
  });

  it("uses a tagged ref when reordering a reading shelf", async () => {
    const request = captureRequest();

    await reorderShelfItem("reading:finished", { moved_book_id: 1 });

    await expect(request).resolves.toMatchObject({ url: "/shelves/reading:finished/items/reorder" });
  });
});

describe("progress API", () => {
  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter;
  });

  it.each<BookProgressUpdate>([
    { unit: "page", value: 0 },
    { unit: "percent", value: 42.5 },
  ])("sends $unit progress as unit and value", async (progress) => {
    const request = captureRequest();

    await addBookProgress(1, progress);

    await expect(request).resolves.toMatchObject({
      url: "/books/1/progress",
      data: JSON.stringify(progress),
    });
  });
});
