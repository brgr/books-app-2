import { QueryClient } from "@tanstack/vue-query";

// How long a persisted cache stays usable: 7 days. Queries are kept in memory just as long, since the persister only
// saves what is still in memory.
export const CACHE_MAX_AGE = 7 * 24 * 60 * 60 * 1000;

export const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      gcTime: CACHE_MAX_AGE,
    },
  },
});
