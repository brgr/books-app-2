import { describe, it, expect, beforeEach, vi } from 'vitest'
import { cachedQuery } from './query'
import { cacheSet, cacheClear, cacheGet } from './store'

describe('cachedQuery', () => {
  beforeEach(async () => {
    await cacheClear()
  })

  it('fetches and caches when cache is empty', async () => {
    const onData = vi.fn()
    const fetcher = vi.fn().mockResolvedValue('network-data')

    await cachedQuery({ key: 'k', fetcher, onData })

    expect(fetcher).toHaveBeenCalledOnce()
    expect(onData).toHaveBeenCalledWith('network-data', 'network')
    const cached = await cacheGet<string>('k')
    expect(cached!.data).toBe('network-data')
  })

  it('returns cached data first, then network data', async () => {
    await cacheSet('k', 'cached-data')

    const calls: Array<[unknown, string]> = []
    const onData = vi.fn((data, source) => calls.push([data, source]))
    const fetcher = vi.fn().mockResolvedValue('fresh-data')

    await cachedQuery({ key: 'k', fetcher, onData })

    expect(calls).toEqual([
      ['cached-data', 'cache'],
      ['fresh-data', 'network'],
    ])
  })

  it('returns cached data and fires onError when fetcher throws', async () => {
    await cacheSet('k', 'cached-data')

    const onData = vi.fn()
    const onError = vi.fn()
    const fetcher = vi.fn().mockRejectedValue(new Error('network failure'))

    await cachedQuery({ key: 'k', fetcher, onData, onError })

    expect(onData).toHaveBeenCalledWith('cached-data', 'cache')
    expect(onData).toHaveBeenCalledTimes(1)
    expect(onError).toHaveBeenCalledWith(expect.any(Error))
  })

  it('fires onError with no data when cache is empty and fetcher throws', async () => {
    const onData = vi.fn()
    const onError = vi.fn()
    const fetcher = vi.fn().mockRejectedValue(new Error('fail'))

    await cachedQuery({ key: 'k', fetcher, onData, onError })

    expect(onData).not.toHaveBeenCalled()
    expect(onError).toHaveBeenCalledWith(expect.any(Error))
  })
})
