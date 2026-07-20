import { describe, it, expect, afterEach } from "vitest";
import type { AxiosAdapter } from "axios";
import { apiClient } from "./client";

const originalAdapter = apiClient.defaults.adapter;

// Answers every request with a fixed body. The guard judges the body itself, not the content-type header, so the
// headers stay empty here.
function respondWith(data: unknown, status = 200) {
  apiClient.defaults.adapter = (async (config) => ({
    data,
    status,
    statusText: "OK",
    headers: {},
    config,
  })) as AxiosAdapter;
}

describe("apiClient JSON guard", () => {
  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter;
  });

  // The failure this guards against: a request misses the backend, the Vite dev server answers with index.html at
  // status 200, and axios hands the app an unparsed string that then reaches the persistent cache.
  it("rejects an HTML body on a JSON request", async () => {
    respondWith("<!doctype html><html></html>");

    await expect(apiClient.get("/books")).rejects.toMatchObject({ code: "ERR_BAD_RESPONSE" });
  });

  it("passes parsed JSON through", async () => {
    respondWith({ items: [] });

    const response = await apiClient.get("/books");

    expect(response.data).toEqual({ items: [] });
  });

  it("allows an empty body, as sent by the 204 endpoints", async () => {
    respondWith("", 204);

    await expect(apiClient.delete("/books/1")).resolves.toBeDefined();
  });
});
