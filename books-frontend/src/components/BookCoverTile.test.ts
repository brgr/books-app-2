import {describe, it, expect} from 'vitest'
import {mount} from '@vue/test-utils'
import BookCoverTile from './BookCoverTile.vue'
import {ReadingStatus, type Book} from '../api/types'

function makeBook(overrides: Partial<Book> = {}): Book {
  return {
    id: 1,
    title: 'Dune',
    author: 'Frank Herbert',
    isbn: null,
    description: null,
    published_date: null,
    page_count: null,
    cover_image_url: null,
    cover_thumbnail_url: null,
    created_at: '',
    updated_at: '',
    user_status: null,
    ...overrides,
  }
}

describe('BookCoverTile', () => {
  it('renders cover image when thumbnail url is present', () => {
    const wrapper = mount(BookCoverTile, {
      props: {book: makeBook({cover_thumbnail_url: '/media/x.jpg'})},
    })
    const img = wrapper.find('img.grid-cover')
    expect(img.exists()).toBe(true)
    expect(img.attributes('alt')).toBe('Dune')
  })

  it('falls back to cover_image_url when thumbnail missing', () => {
    const wrapper = mount(BookCoverTile, {
      props: {book: makeBook({cover_image_url: '/media/full.jpg'})},
    })
    expect(wrapper.find('img.grid-cover').exists()).toBe(true)
  })

  it('renders placeholder with title when no cover urls', () => {
    const wrapper = mount(BookCoverTile, {props: {book: makeBook()}})
    expect(wrapper.find('img.grid-cover').exists()).toBe(false)
    const placeholder = wrapper.find('.grid-cover-placeholder')
    expect(placeholder.exists()).toBe(true)
    expect(placeholder.text()).toContain('Dune')
  })

  it('emits "click" with book id when tile is clicked', async () => {
    const wrapper = mount(BookCoverTile, {props: {book: makeBook({id: 42})}})
    await wrapper.find('button.grid-cover-link').trigger('click')
    expect(wrapper.emitted('click')?.[0]?.[0]).toBe(42)
  })

  it('does not show progress badge by default', () => {
    const wrapper = mount(BookCoverTile, {
      props: {
        book: makeBook({
          page_count: 200,
          user_status: {
            status: ReadingStatus.STARTED,
            current_page: 50,
          } as Book['user_status'],
        }),
      },
    })
    expect(wrapper.find('.grid-progress-badge').exists()).toBe(false)
  })

  it('shows progress badge when showProgress prop is true and book is STARTED with page data', () => {
    const wrapper = mount(BookCoverTile, {
      props: {
        showProgress: true,
        book: makeBook({
          page_count: 200,
          user_status: {
            status: ReadingStatus.STARTED,
            current_page: 50,
          } as Book['user_status'],
        }),
      },
    })
    const badge = wrapper.find('.grid-progress-badge')
    expect(badge.exists()).toBe(true)
    expect(badge.text()).toContain('25%')
  })

  it('hides progress badge when showProgress=true but status is not STARTED', () => {
    const wrapper = mount(BookCoverTile, {
      props: {
        showProgress: true,
        book: makeBook({
          page_count: 200,
          user_status: {
            status: ReadingStatus.WANT_TO_READ,
            current_page: 50,
          } as Book['user_status'],
        }),
      },
    })
    expect(wrapper.find('.grid-progress-badge').exists()).toBe(false)
  })
})
