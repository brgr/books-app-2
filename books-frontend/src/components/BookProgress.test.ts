import {describe, it, expect, vi} from 'vitest'
import {mount} from '@vue/test-utils'
import BookProgress from './BookProgress.vue'

function makeProps(overrides: Partial<{
  currentPage: number | null
  pageCount: number | null
  canUpdate: boolean
  saving: boolean
}> = {}) {
  return {
    currentPage: null,
    pageCount: null,
    canUpdate: true,
    saving: false,
    ...overrides,
  }
}

describe('BookProgress', () => {
  it('shows "No progress yet" when currentPage is null', () => {
    const wrapper = mount(BookProgress, {props: makeProps()})
    expect(wrapper.text()).toContain('No progress yet')
  })

  it('shows "Page X of Y" when both currentPage and pageCount are set', () => {
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 50, pageCount: 200})})
    expect(wrapper.text()).toContain('Page 50 of 200')
  })

  it('shows "Page X" when only currentPage is set', () => {
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 50})})
    expect(wrapper.text()).toContain('Page 50')
    expect(wrapper.text()).not.toContain('of')
  })

  it('shows hint when canUpdate is false', () => {
    const wrapper = mount(BookProgress, {props: makeProps({canUpdate: false})})
    expect(wrapper.text()).toContain('Start reading to track progress')
  })

  it('switches to edit mode when Update is clicked', async () => {
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 10})})
    await wrapper.find('[data-test="update"]').trigger('click')
    expect(wrapper.find('input[type="number"]').exists()).toBe(true)
  })

  it('emits "save" with parsed page number when Save is clicked', async () => {
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 10})})
    await wrapper.find('[data-test="update"]').trigger('click')
    await wrapper.find('input[type="number"]').setValue('42')
    await wrapper.find('[data-test="save"]').trigger('click')
    expect(wrapper.emitted('save')?.[0]?.[0]).toBe(42)
  })

  it('does not emit "save" when input is empty', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 10})})
    await wrapper.find('[data-test="update"]').trigger('click')
    await wrapper.find('input[type="number"]').setValue('')
    await wrapper.find('[data-test="save"]').trigger('click')
    expect(wrapper.emitted('save')).toBeFalsy()
    expect(alertSpy).toHaveBeenCalled()
    alertSpy.mockRestore()
  })

  it('does not emit "save" when input is negative', async () => {
    const alertSpy = vi.spyOn(window, 'alert').mockImplementation(() => {})
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 10})})
    await wrapper.find('[data-test="update"]').trigger('click')
    await wrapper.find('input[type="number"]').setValue('-5')
    await wrapper.find('[data-test="save"]').trigger('click')
    expect(wrapper.emitted('save')).toBeFalsy()
    alertSpy.mockRestore()
  })

  it('Cancel exits edit mode without emitting', async () => {
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 10})})
    await wrapper.find('[data-test="update"]').trigger('click')
    await wrapper.find('input[type="number"]').setValue('99')
    await wrapper.find('[data-test="cancel"]').trigger('click')
    expect(wrapper.emitted('save')).toBeFalsy()
    expect(wrapper.find('input[type="number"]').exists()).toBe(false)
  })

  it('exits edit mode when currentPage prop changes', async () => {
    const wrapper = mount(BookProgress, {props: makeProps({currentPage: 10})})
    await wrapper.find('[data-test="update"]').trigger('click')
    await wrapper.setProps({currentPage: 20})
    expect(wrapper.find('input[type="number"]').exists()).toBe(false)
  })

  it('disables Update button when canUpdate is false', () => {
    const wrapper = mount(BookProgress, {props: makeProps({canUpdate: false})})
    const btn = wrapper.find('[data-test="update"]').element as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })
})
