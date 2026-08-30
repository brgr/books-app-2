import { afterEach, describe, expect, it } from "vitest";
import type { AxiosAdapter, InternalAxiosRequestConfig } from "axios";
import { apiClient } from "./client";
import { getShelfBooks, reorderShelfItem } from "./books";

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
