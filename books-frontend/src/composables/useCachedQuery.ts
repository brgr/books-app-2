import { ref, watch, toValue, isRef, type Ref } from "vue";
import { cachedQuery } from "../cache/query";
import { cacheDel, cacheSet } from "../cache/store";

type MaybeRefOrGetter<T> = T | Ref<T> | (() => T);

export function useCachedQuery<T>(
  key: MaybeRefOrGetter<string>,
  fetcher: () => Promise<T>,
  options?: { enabled?: MaybeRefOrGetter<boolean> },
) {
  const data = ref<T | null>(null) as Ref<T | null>;
  const isStale = ref(false);
  const error = ref<unknown>(null);

  let generation = 0;
  let currentPromise: Promise<void> = Promise.resolve();

  function execute() {
    const currentKey = toValue(key);
    if (!currentKey) return;

    const enabled = options?.enabled !== undefined ? toValue(options.enabled) : true;
    if (!enabled) return;

    const gen = ++generation;
    error.value = null;

    currentPromise = cachedQuery<T>({
      key: currentKey,
      fetcher,
      isCurrent: () => gen === generation,
      onData: (d, source) => {
        if (gen !== generation) return;
        data.value = d;
        isStale.value = source === "cache";
      },
      onError: (err) => {
        if (gen !== generation) return;
        error.value = err;
      },
    });
  }

  async function refresh() {
    execute();
    await currentPromise;
  }

  async function invalidate() {
    const currentKey = toValue(key);
    await cacheDel(currentKey);
    execute();
    await currentPromise;
  }

  /**
   * Optimistically replace the value (e.g. after a persisted mutation) and mirror it into the cache entry, so a later
   * remount serves the new value rather than the stale one.
   */
  async function setData(next: T) {
    data.value = next;
    const currentKey = toValue(key);
    if (!currentKey) return;
    await cacheSet(currentKey, next);
  }

  if (isRef(key) || typeof key === "function") {
    watch(
      () => toValue(key),
      () => execute(),
      { immediate: true },
    );
  } else {
    execute();
  }

  if (options?.enabled !== undefined && (isRef(options.enabled) || typeof options.enabled === "function")) {
    watch(
      () => toValue(options.enabled!),
      (val) => {
        if (val) execute();
      },
    );
  }

  return { data: data as Readonly<Ref<T | null>>, isStale, error, setData, refresh, invalidate };
}
