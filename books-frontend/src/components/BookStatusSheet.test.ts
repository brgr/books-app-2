import {describe, it, expect} from 'vitest'
import {mount} from '@vue/test-utils'
import BookStatusSheet from './BookStatusSheet.vue'

function makeProps(overrides: Partial<{
  currentPage: number | null
  pageCount: number | null
  progressSaving: boolean
}> = {}) {
  return {
    currentPage: 10,
    pageCount: 200,
    progressSaving: false,
    ...overrides,
  }
}

describe('BookStatusSheet', () => {
  it('shows current progress summary', () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({currentPage: 50, pageCount: 200})})
    expect(wrapper.text()).toContain('Page 50')
    expect(wrapper.text()).toContain('of 200')
  })

  it('shows "No progress yet" when current page is null', () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({currentPage: null})})
    expect(wrapper.text()).toContain('No progress yet')
  })

  it('hides progress input until Update is clicked', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps()})
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false)
    await wrapper.find('[data-test="edit-progress"]').trigger('click')
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(true)
  })

  it('emits "update-progress" with parsed page number when Save is clicked', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps()})
    await wrapper.find('[data-test="edit-progress"]').trigger('click')
    await wrapper.find('[data-test="save-progress"]').trigger('click')
    expect(wrapper.emitted('update-progress')?.[0]?.[0]).toBe(10)
  })

  it('emits "update-progress" with new page after editing the input', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps()})
    await wrapper.find('[data-test="edit-progress"]').trigger('click')
    await wrapper.find('[data-test="progress-input"]').setValue('42')
    await wrapper.find('[data-test="save-progress"]').trigger('click')
    expect(wrapper.emitted('update-progress')?.[0]?.[0]).toBe(42)
  })

  it('Cancel exits edit mode without emitting', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps()})
    await wrapper.find('[data-test="edit-progress"]').trigger('click')
    await wrapper.find('[data-test="progress-input"]').setValue('99')
    await wrapper.find('[data-test="cancel-progress"]').trigger('click')
    expect(wrapper.emitted('update-progress')).toBeFalsy()
    expect(wrapper.find('[data-test="progress-input"]').exists()).toBe(false)
  })
})
