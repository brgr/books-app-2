import {describe, it, expect, vi} from 'vitest'
import {mount} from '@vue/test-utils'
import BookStatusSheet from './BookStatusSheet.vue'
import {ReadingStatus} from '../api/types'

function makeProps(overrides: Partial<{
  status: ReadingStatus | null
  statusLabel: string
  statusSubtitle: string
  updating: boolean
  currentPage: number | null
  pageCount: number | null
  progressSaving: boolean
}> = {}) {
  return {
    status: null,
    statusLabel: 'Want to read',
    statusSubtitle: 'Not started yet',
    updating: false,
    ...overrides,
  }
}

describe('BookStatusSheet', () => {
  it('renders header with status label and subtitle', () => {
    const wrapper = mount(BookStatusSheet, {
      props: makeProps({statusLabel: 'Reading', statusSubtitle: 'Page 50 of 200'}),
    })
    expect(wrapper.text()).toContain('Reading')
    expect(wrapper.text()).toContain('Page 50 of 200')
  })

  it('shows Start Reading button when status is null', () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({status: null})})
    expect(wrapper.text()).toContain('Start Reading')
    expect(wrapper.text()).not.toContain('Finish Reading')
  })

  it('shows Start Reading button when status is WANT_TO_READ', () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({status: ReadingStatus.WANT_TO_READ})})
    expect(wrapper.text()).toContain('Start Reading')
  })

  it('shows Finish Reading button when status is STARTED', () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({status: ReadingStatus.STARTED})})
    expect(wrapper.text()).toContain('Finish Reading')
    expect(wrapper.text()).not.toContain('Start Reading')
  })

  it('shows neither button when status is FINISHED', () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({status: ReadingStatus.FINISHED})})
    expect(wrapper.text()).not.toContain('Start Reading')
    expect(wrapper.text()).not.toContain('Finish Reading')
  })

  it('emits "start" with occurred-at when Start Reading is clicked', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({status: null})})
    await wrapper.find('[data-test="start-reading"]').trigger('click')
    expect(wrapper.emitted('start')).toBeTruthy()
    expect(wrapper.emitted('start')?.[0]?.[0]).toBeTypeOf('object')
  })

  it('emits "finish" when Finish Reading is clicked', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps({status: ReadingStatus.STARTED})})
    await wrapper.find('[data-test="finish-reading"]').trigger('click')
    expect(wrapper.emitted('finish')).toBeTruthy()
  })

  it('emits "close" when overlay is clicked', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps()})
    await wrapper.find('[data-test="overlay"]').trigger('click.self')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('emits "close" when Close button is clicked', async () => {
    const wrapper = mount(BookStatusSheet, {props: makeProps()})
    await wrapper.find('[data-test="close"]').trigger('click')
    expect(wrapper.emitted('close')).toBeTruthy()
  })

  it('disables action button while updating', () => {
    const wrapper = mount(BookStatusSheet, {
      props: makeProps({status: null, updating: true}),
    })
    const btn = wrapper.find('[data-test="start-reading"]').element as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('emits undefined occurredAt when date is today', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-26T10:00:00'))

    const wrapper = mount(BookStatusSheet, {props: makeProps({status: null})})
    await wrapper.find('[data-test="start-reading"]').trigger('click')

    const payload = wrapper.emitted('start')?.[0]?.[0] as {occurredAt?: string}
    expect(payload.occurredAt).toBeUndefined()

    vi.useRealTimers()
  })

  it('emits "update-progress" with parsed page number when Save progress is clicked', async () => {
    const wrapper = mount(BookStatusSheet, {
      props: makeProps({status: ReadingStatus.STARTED, currentPage: 10, pageCount: 200}),
    })
    await wrapper.find('[data-test="save-progress"]').trigger('click')
    expect(wrapper.emitted('update-progress')?.[0]?.[0]).toBe(10)
  })

  it('emits "update-progress" with new page after editing the input', async () => {
    const wrapper = mount(BookStatusSheet, {
      props: makeProps({status: ReadingStatus.STARTED, currentPage: 10, pageCount: 200}),
    })
    await wrapper.find('[data-test="progress-input"]').setValue('42')
    await wrapper.find('[data-test="save-progress"]').trigger('click')
    expect(wrapper.emitted('update-progress')?.[0]?.[0]).toBe(42)
  })

  it('emits ISO occurredAt when a past date is picked', async () => {
    vi.useFakeTimers()
    vi.setSystemTime(new Date('2026-04-26T10:00:00'))

    const wrapper = mount(BookStatusSheet, {props: makeProps({status: null})})
    const dateInput = wrapper.find('[data-test="date-input"]').element as HTMLInputElement
    dateInput.value = '2026-04-20'
    await wrapper.find('[data-test="date-input"]').trigger('input')
    await wrapper.find('[data-test="start-reading"]').trigger('click')

    const payload = wrapper.emitted('start')?.[0]?.[0] as {occurredAt?: string}
    expect(payload.occurredAt).toBeDefined()
    expect(payload.occurredAt).toContain('2026-04-20')

    vi.useRealTimers()
  })
})
