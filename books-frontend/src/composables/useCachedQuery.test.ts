import { describe, it, expect, beforeEach, vi } from 'vitest'
import { ref, nextTick } from 'vue'
import { useCachedQuery } from './useCachedQuery'
import { cacheSet, cacheClear } from '../cache/store'

async function flushPromises() {
  for (let i = 0; i < 5; i++) {
    await new Promise<void>(r => setTimeout(r, 0))
  }
}

describe('useCachedQuery', () => {
  beforeEach(async () => {
    await cacheClear()
  })

  it('fetches from network when cache is empty', async () => {
    const fetcher = vi.fn().mockResolvedValue('fresh')

    const { data } = useCachedQuery('key', fetcher)

    expect(data.value).toBeNull()

    await flushPromises()

    expect(data.value).toBe('fresh')
  })

  it('serves cached data first, then updates with network data', async () => {
    await cacheSet('key', 'cached')
    const fetcher = vi.fn().mockResolvedValue('fresh')

    const { data, isStale } = useCachedQuery('key', fetcher)

    await flushPromises()

    expect(data.value).toBe('fresh')
    expect(isStale.value).toBe(false)
  })

  it('sets isStale to true when showing cached data', async () => {
    await cacheSet('key', 'cached')
    let resolveFetch: (v: string) => void
    const fetcher = vi.fn().mockReturnValue(new Promise<string>(r => { resolveFetch = r }))

    const { data, isStale } = useCachedQuery('key', fetcher)

    await flushPromises()

    expect(data.value).toBe('cached')
    expect(isStale.value).toBe(true)

    resolveFetch!('fresh')
    await flushPromises()

    expect(data.value).toBe('fresh')
    expect(isStale.value).toBe(false)
  })

  it('sets error when fetcher fails and cache is empty', async () => {
    const fetcher = vi.fn().mockRejectedValue(new Error('fail'))

    const { data, error } = useCachedQuery('key', fetcher)

    await flushPromises()

    expect(data.value).toBeNull()
    expect(error.value).toBeInstanceOf(Error)
  })

  it('keeps cached data when fetcher fails', async () => {
    await cacheSet('key', 'cached')
    const fetcher = vi.fn().mockRejectedValue(new Error('fail'))

    const { data, error } = useCachedQuery('key', fetcher)

    await flushPromises()

    expect(data.value).toBe('cached')
    expect(error.value).toBeInstanceOf(Error)
  })

  it('refresh re-fetches data', async () => {
    const fetcher = vi.fn().mockResolvedValue('v1')

    const { data, refresh } = useCachedQuery('key', fetcher)
    await flushPromises()
    expect(data.value).toBe('v1')

    fetcher.mockResolvedValue('v2')
    await refresh()

    expect(data.value).toBe('v2')
  })

  it('invalidate clears cache and re-fetches', async () => {
    await cacheSet('key', 'old-cached')
    const fetcher = vi.fn().mockResolvedValue('new')

    const { data, invalidate } = useCachedQuery('key', fetcher)
    await flushPromises()

    await invalidate()

    expect(data.value).toBe('new')
  })

  it('reacts to key changes', async () => {
    const key = ref('books:1')
    const fetcher = vi.fn().mockImplementation(async () => `data-for-${key.value}`)

    const { data } = useCachedQuery(key, fetcher)
    await flushPromises()
    expect(data.value).toBe('data-for-books:1')

    key.value = 'books:2'
    await nextTick()
    await flushPromises()

    expect(data.value).toBe('data-for-books:2')
  })

  it('does not fetch when enabled is false', async () => {
    const fetcher = vi.fn().mockResolvedValue('data')
    const enabled = ref(false)

    const { data } = useCachedQuery('key', fetcher, { enabled })
    await flushPromises()

    expect(fetcher).not.toHaveBeenCalled()
    expect(data.value).toBeNull()

    enabled.value = true
    await nextTick()
    await flushPromises()

    expect(fetcher).toHaveBeenCalledOnce()
    expect(data.value).toBe('data')
  })
})
