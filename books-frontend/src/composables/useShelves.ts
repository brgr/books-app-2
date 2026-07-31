import { computed } from "vue";
import { getShelves } from "../api/books";
import type { Shelf } from "../api/types";
import { cacheKeys } from "../cache/keys";
import { useCachedQuery } from "./useCachedQuery";

let sharedQuery: ReturnType<typeof useCachedQuery<Shelf[]>> | null = null;

export function useShelves() {
  sharedQuery ??= useCachedQuery<Shelf[]>(cacheKeys.shelves(), () => getShelves());
  const query = sharedQuery;

  return { shelves: computed(() => query.data.value ?? []) };
}

/** Drops the shared query (only needed for testing). */
export function resetShelves() {
  sharedQuery = null;
}
