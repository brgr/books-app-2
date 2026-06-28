import {describe, it, expect} from 'vitest'
import {mount} from '@vue/test-utils'
import {nextTick} from 'vue'
import BookNotes from './BookNotes.vue'

describe('BookNotes', () => {
  it('renders markdown when notes are present', () => {
    const wrapper = mount(BookNotes, {props: {notes: '**bold** text', saving: false}})
    expect(wrapper.html()).toContain('<strong>bold</strong>')
  })

  it('shows empty state when notes are blank', () => {
    const wrapper = mount(BookNotes, {props: {notes: '', saving: false}})
    expect(wrapper.text()).toContain('No notes yet')
  })

  it('switches to edit mode when Update is clicked', async () => {
    const wrapper = mount(BookNotes, {props: {notes: 'hello', saving: false}})
    await wrapper.find('[data-test="edit"]').trigger('click')
    expect(wrapper.find('textarea').exists()).toBe(true)
  })

  it('emits "save" with current draft when Save is clicked', async () => {
    const wrapper = mount(BookNotes, {props: {notes: 'old', saving: false}})
    await wrapper.find('[data-test="edit"]').trigger('click')
    const textarea = wrapper.find('textarea')
    await textarea.setValue('new note')
    await wrapper.find('[data-test="save"]').trigger('click')
    expect(wrapper.emitted('save')).toBeTruthy()
    expect(wrapper.emitted('save')?.[0]?.[0]).toBe('new note')
  })

  it('disables Save when draft is unchanged', async () => {
    const wrapper = mount(BookNotes, {props: {notes: 'same', saving: false}})
    await wrapper.find('[data-test="edit"]').trigger('click')
    const btn = wrapper.find('[data-test="save"]').element as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })

  it('Cancel reverts the draft and exits edit mode', async () => {
    const wrapper = mount(BookNotes, {props: {notes: 'old', saving: false}})
    await wrapper.find('[data-test="edit"]').trigger('click')
    await wrapper.find('textarea').setValue('temporary')
    await wrapper.find('[data-test="cancel"]').trigger('click')
    expect(wrapper.find('textarea').exists()).toBe(false)
    expect(wrapper.html()).not.toContain('temporary')
  })

  it('exits edit mode when notes prop changes (e.g. after save)', async () => {
    const wrapper = mount(BookNotes, {props: {notes: 'old', saving: false}})
    await wrapper.find('[data-test="edit"]').trigger('click')
    await wrapper.setProps({notes: 'fresh from server'})
    await nextTick()
    expect(wrapper.find('textarea').exists()).toBe(false)
  })

  it('disables Save while saving', async () => {
    const wrapper = mount(BookNotes, {props: {notes: 'old', saving: false}})
    await wrapper.find('[data-test="edit"]').trigger('click')
    await wrapper.find('textarea').setValue('new')
    await wrapper.setProps({saving: true})
    const btn = wrapper.find('[data-test="save"]').element as HTMLButtonElement
    expect(btn.disabled).toBe(true)
  })
})
