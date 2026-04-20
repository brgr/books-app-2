import { cacheGet, cacheSet } from './store'

export interface CachedQueryOptions<T> {
  key: string
  fetcher: () => Promise<T>
  onData: (data: T, source: 'cache' | 'network') => void
  onError?: (error: unknown) => void
}

export async function cachedQuery<T>(options: CachedQueryOptions<T>): Promise<void> {
  const { key, fetcher, onData, onError } = options

  const cached = await cacheGet<T>(key)
  if (cached) {
    onData(cached.data, 'cache')
  }

  try {
    const data = await fetcher()
    await cacheSet(key, data)
    onData(data, 'network')
  } catch (err) {
    onError?.(err)
  }
}
