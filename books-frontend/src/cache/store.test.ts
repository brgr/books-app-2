import { describe, it, expect, beforeEach } from 'vitest'
import { cacheGet, cacheSet, cacheDel, cacheInvalidateByPrefix, cacheClear } from './store'

describe('cache store', () => {
  beforeEach(async () => {
    await cacheClear()
  })

  it('returns undefined for a missing key', async () => {
    const result = await cacheGet('nonexistent')
    expect(result).toBeUndefined()
  })

  it('stores and retrieves a value with timestamp', async () => {
    const before = Date.now()
    await cacheSet('test-key', { hello: 'world' })
    const after = Date.now()

    const entry = await cacheGet<{ hello: string }>('test-key')
    expect(entry).toBeDefined()
    expect(entry!.data).toEqual({ hello: 'world' })
    expect(entry!.timestamp).toBeGreaterThanOrEqual(before)
    expect(entry!.timestamp).toBeLessThanOrEqual(after)
  })

  it('overwrites an existing entry', async () => {
    await cacheSet('key', 'first')
    await cacheSet('key', 'second')

    const entry = await cacheGet<string>('key')
    expect(entry!.data).toBe('second')
  })

  it('deletes an entry', async () => {
    await cacheSet('key', 'value')
    await cacheDel('key')

    const result = await cacheGet('key')
    expect(result).toBeUndefined()
  })

  it('invalidates entries by prefix', async () => {
    await cacheSet('books:42', 'book data')
    await cacheSet('books:42:events', 'events data')
    await cacheSet('books:99', 'other book')
    await cacheSet('lists', 'lists data')

    await cacheInvalidateByPrefix('books:42')

    expect(await cacheGet('books:42')).toBeUndefined()
    expect(await cacheGet('books:42:events')).toBeUndefined()
    expect(await cacheGet('books:99')).toBeDefined()
    expect(await cacheGet('lists')).toBeDefined()
  })

  it('clears all entries', async () => {
    await cacheSet('a', 1)
    await cacheSet('b', 2)
    await cacheClear()

    expect(await cacheGet('a')).toBeUndefined()
    expect(await cacheGet('b')).toBeUndefined()
  })
})
