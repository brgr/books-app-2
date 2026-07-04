import {describe, it, expect} from 'vitest'
import {mount} from '@vue/test-utils'
import BookProgressBar from './BookProgressBar.vue'

describe('BookProgressBar', () => {
  it('renders the percentage from current page and page count', () => {
    const wrapper = mount(BookProgressBar, {props: {currentPage: 50, pageCount: 200}})
    expect(wrapper.find('.bar-percent').text()).toBe('25%')
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('width: 25%')
  })

  it('clamps the percentage to 100 when past the page count', () => {
    const wrapper = mount(BookProgressBar, {props: {currentPage: 250, pageCount: 200}})
    expect(wrapper.find('.bar-percent').text()).toBe('100%')
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('width: 100%')
  })

  it('shows a dash and an empty bar when page count is missing', () => {
    const wrapper = mount(BookProgressBar, {props: {currentPage: 50, pageCount: null}})
    expect(wrapper.find('.bar-percent').text()).toBe('—')
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('width: 0%')
  })

  it('shows an empty bar when there is no current page', () => {
    const wrapper = mount(BookProgressBar, {props: {currentPage: null, pageCount: 200}})
    expect(wrapper.find('.bar-percent').text()).toBe('0%')
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('width: 0%')
  })

  it('uses currentPercent directly, ignoring page and page count', () => {
    const wrapper = mount(BookProgressBar, {props: {currentPage: null, currentPercent: 60, pageCount: null}})
    expect(wrapper.find('.bar-percent').text()).toBe('60%')
    expect(wrapper.find('.bar-fill').attributes('style')).toContain('width: 60%')
  })
})
