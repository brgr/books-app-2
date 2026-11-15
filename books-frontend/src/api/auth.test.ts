import { describe, it, expect, afterEach } from "vitest";
import { AxiosError, type AxiosAdapter } from "axios";
import { queryClient } from "../query/client";
import { checkAuthStatus, isAuthenticated } from "./auth";
import { apiClient } from "./client";

const originalAdapter = apiClient.defaults.adapter;

function failWith(error: (config: Parameters<AxiosAdapter>[0]) => AxiosError) {
  apiClient.defaults.adapter = (async (config) => {
    throw error(config);
  }) as AxiosAdapter;
}

describe("checkAuthStatus", () => {
  afterEach(() => {
    apiClient.defaults.adapter = originalAdapter;
    queryClient.clear();
  });

  it("keeps the session and the cached data when the server can't be reached", async () => {
    queryClient.setQueryData(["shelves", "list"], []);
    failWith((config) => new AxiosError("Network Error", AxiosError.ERR_NETWORK, config));

    expect(await checkAuthStatus()).toBe(true);
    expect(isAuthenticated()).toBe(true);
    expect(queryClient.getQueryData(["shelves", "list"])).toEqual([]);
  });

  it("reports a session the server rejects as ended", async () => {
    failWith(
      (config) =>
        new AxiosError("Unauthorized", AxiosError.ERR_BAD_REQUEST, config, undefined, {
          data: null,
          status: 401,
          statusText: "Unauthorized",
          headers: {},
          config,
        }),
    );

    expect(await checkAuthStatus()).toBe(false);
    expect(isAuthenticated()).toBe(false);
  });
});
