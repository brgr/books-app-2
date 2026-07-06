import { cacheGet, cacheSet } from "./store";

export interface CachedQueryOptions<T> {
  key: string;
  fetcher: () => Promise<T>;
  onData: (data: T, source: "cache" | "network") => void;
  onError?: (error: unknown) => void;
  // Returns false when this call has been superseded (e.g. the caller switched to a different key).
  // A stale call must not write to the cache, since its fetcher may have resolved data for a different resource than
  // `key` names.
  isCurrent?: () => boolean;
}

export async function cachedQuery<T>(options: CachedQueryOptions<T>): Promise<void> {
  const { key, fetcher, onData, onError, isCurrent } = options;
  const stillCurrent = () => (isCurrent ? isCurrent() : true);

  const cached = await cacheGet<T>(key);
  if (cached && stillCurrent()) {
    onData(cached.data, "cache");
  }

  try {
    const data = await fetcher();
    if (!stillCurrent()) return;
    await cacheSet(key, data);
    onData(data, "network");
  } catch (err) {
    if (!stillCurrent()) return;
    onError?.(err);
  }
}
