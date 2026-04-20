import { describe, it, expect } from 'vitest'
import { cacheKeys } from './keys'

describe('cacheKeys', () => {
  it('generates key for lists', () => {
    expect(cacheKeys.lists()).toBe('lists')
  })

  it('generates key for list books with pagination', () => {
    expect(cacheKeys.listBooks(5, 1, 20)).toBe('lists:5:books:page=1&pageSize=20')
  })

  it('generates key for a single book', () => {
    expect(cacheKeys.book(42)).toBe('books:42')
  })

  it('generates key for book events', () => {
    expect(cacheKeys.bookEvents(42)).toBe('books:42:events')
  })
})
