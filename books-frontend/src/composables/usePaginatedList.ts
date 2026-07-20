import { computed, type ComputedRef, type MaybeRefOrGetter, ref, type Ref, toValue, watch } from "vue";
import { cachedQuery } from "../cache/query";
import { cacheInvalidateByPrefix } from "../cache/store";

/** One page of a paginated resource, as returned by the API. */
export interface PageResult<T> {
  items: T[];
  page: number;
  pages: number;
}

export interface PaginatedListOptions<T, R extends string | number> {
  /**
   * Identifies the resource being paginated. `null` disables fetching. Changing
   * it resets pagination and reloads page 1.
   * This is the single place that owns "which resource am I paging", so the caller never juggles page state.
   */
  resourceId: MaybeRefOrGetter<R | null>;
  /** Cache key for a page of the given resource (per-page, stale-while-revalidate). */
  cacheKey: (resourceId: R, page: number) => string;
  /** Fetches a page of the given resource. */
  fetchPage: (resourceId: R, page: number) => Promise<PageResult<T>>;
  /** Stable identity used to de-duplicate items when appending later pages. */
  itemKey: (item: T) => string | number;
  /**
   * Prefix covering every cached page of the resource. Used by `replaceItems` to invalidate the whole resource after
   * an optimistic reorder — required so an optimistic update can never silently leave the cache stale.
   */
  cacheKeyPrefix: (resourceId: R) => string;
}

export interface PaginatedList<T> {
  /**
   * Accumulated items across all loaded pages. Read-only; updates go through `replaceItems` to ensure
   * cache invalidation.
   */
  items: Readonly<Ref<T[]>>;
  /**
   * Optimistically replace the accumulated items (e.g. after a persisted reorder). Updates the in-memory list and
   * invalidates the resource's cached pages so a later remount refetches the new order rather than serving the old
   * one. Cache invalidation requires `cacheKeyPrefix`.
   */
  replaceItems: (next: T[]) => Promise<void>;
  /** Whether another page exists beyond what's loaded. */
  hasMore: ComputedRef<boolean>;
  /** True while page 1 of the current resource is loading (drives skeleton / empty gating). */
  isLoading: Ref<boolean>;
  /** True while a subsequent page is loading (drives the infinite-scroll spinner). */
  isLoadingMore: Ref<boolean>;
  /** True once page 1 of the current resource has resolved at least once. */
  loaded: Ref<boolean>;
  error: Ref<unknown>;
  /** Advance to the next page, if any. No-ops unless a page is available. */
  loadMore: () => void;
  /** Reset to page 1 and refetch the current resource. */
  reload: () => Promise<void>;
}

/**
 * Cursor-based accumulation over a paginated API, keyed by *resource* rather than by page.
 *
 * Unlike `useCachedQuery` (a single-value, latest-wins primitive), sequential pages here are additive,
 * not competing versions of one value.
 */
export function usePaginatedList<T, R extends string | number = number>(
  options: PaginatedListOptions<T, R>,
): PaginatedList<T> {
  const items = ref<T[]>([]) as Ref<T[]>;
  const page = ref(1);
  const totalPages = ref(0);
  const isLoading = ref(false);
  const isLoadingMore = ref(false);
  const loaded = ref(false);
  const error = ref<unknown>(null);

  // Every fetch is a generation; a superseded fetch (resource switch or a later page) never writes back. `run`
  // bumps this, and an in-flight response is dropped the moment the next `run` starts.
  let generation = 0;

  const hasMore = computed(() => page.value < totalPages.value);

  function ingest(data: PageResult<T>) {
    totalPages.value = data.pages;

    if (data.page <= 1) {
      items.value = [...data.items];
    } else {
      const seen = new Set(items.value.map(options.itemKey));
      items.value = [...items.value, ...data.items.filter((item) => !seen.has(options.itemKey(item)))];
    }
  }

  function reset() {
    page.value = 1;
    totalPages.value = 0;
    items.value = [];
    loaded.value = false;
    error.value = null;
  }

  async function run(targetPage: number) {
    const resourceId = toValue(options.resourceId);
    const gen = ++generation;

    if (resourceId === null) return; // generation bumped above → supersedes any in-flight fetch

    const isFirstPage = targetPage === 1;
    error.value = null;

    if (isFirstPage) {
      isLoading.value = true;
    } else {
      isLoadingMore.value = true;
    }

    await cachedQuery<PageResult<T>>({
      key: options.cacheKey(resourceId, targetPage),
      fetcher: () => options.fetchPage(resourceId, targetPage),
      isCurrent: () => gen === generation,
      onData: (data) => {
        if (gen !== generation) return;
        ingest(data);
        if (isFirstPage) loaded.value = true;
      },
      onError: (err) => {
        if (gen === generation) error.value = err;
      },
    });

    if (gen === generation) {
      isLoading.value = false;
      isLoadingMore.value = false;
    }
  }

  async function reload() {
    reset();
    await run(1);
  }

  async function replaceItems(next: T[]) {
    items.value = [...next];
    const resourceId = toValue(options.resourceId);
    if (resourceId === null) return;
    await cacheInvalidateByPrefix(options.cacheKeyPrefix(resourceId));
  }

  function loadMore() {
    if (isLoadingMore.value || !hasMore.value) return;
    page.value += 1;
    void run(page.value);
  }

  // The resource is the single trigger: switching it resets and reloads
  watch(
    () => toValue(options.resourceId),
    () => void reload(),
    { immediate: true },
  );

  return { items, replaceItems, hasMore, isLoading, isLoadingMore, loaded, error, loadMore, reload };
}
