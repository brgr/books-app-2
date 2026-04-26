import {describe, it, expect, afterEach} from 'vitest'
import {ref, nextTick, defineComponent, h, type Ref} from 'vue'
import {mount} from '@vue/test-utils'
import {useClampToggle} from './useClampToggle'

interface HostExposed {
  el: HTMLElement | null
  expanded: boolean
  showToggle: boolean
  maxHeight: string
  update: () => void
  toggle: () => void
}

function mountHost(opts: {scrollHeight: number; lineHeight?: number; source?: Ref<unknown>}) {
  const Host = defineComponent({
    setup() {
      const el = ref<HTMLElement | null>(null)
      const api = useClampToggle(el, {source: opts.source})
      return {el, ...api}
    },
    render() {
      return h('p', {ref: 'el'}, 'content')
    },
  })

  const wrapper = mount(Host, {attachTo: document.body})
  const node = wrapper.element as HTMLElement

  Object.defineProperty(node, 'scrollHeight', {
    configurable: true,
    get: () => opts.scrollHeight,
  })
  const origGetComputed = window.getComputedStyle
  window.getComputedStyle = ((el: Element) => {
    const styles = origGetComputed(el)
    return new Proxy(styles, {
      get(target, prop) {
        if (prop === 'lineHeight') return `${opts.lineHeight ?? 20}px`
        if (prop === 'fontSize') return '16px'
        return Reflect.get(target, prop)
      },
    })
  }) as typeof window.getComputedStyle

  return {wrapper, vm: wrapper.vm as unknown as HostExposed, restore: () => { window.getComputedStyle = origGetComputed }}
}

describe('useClampToggle', () => {
  let cleanups: Array<() => void> = []

  afterEach(() => {
    cleanups.forEach(c => c())
    cleanups = []
    document.body.innerHTML = ''
  })

  it('shows the toggle when content overflows the clamp height', async () => {
    const {vm, restore} = mountHost({scrollHeight: 200, lineHeight: 20})
    cleanups.push(restore)
    vm.update()
    expect(vm.showToggle).toBe(true)
  })

  it('hides the toggle when content fits within the clamp height', async () => {
    const {vm, restore} = mountHost({scrollHeight: 40, lineHeight: 20})
    cleanups.push(restore)
    vm.update()
    expect(vm.showToggle).toBe(false)
  })

  it('starts collapsed with maxHeight equal to clamp height', async () => {
    const {vm, restore} = mountHost({scrollHeight: 200, lineHeight: 20})
    cleanups.push(restore)
    vm.update()
    expect(vm.expanded).toBe(false)
    expect(vm.maxHeight).toBe('60px')
  })

  it('toggle() expands then collapses', async () => {
    const {vm, restore} = mountHost({scrollHeight: 200, lineHeight: 20})
    cleanups.push(restore)
    vm.update()
    vm.toggle()
    expect(vm.expanded).toBe(true)
    vm.toggle()
    expect(vm.expanded).toBe(false)
  })

  it('resets to collapsed when source ref changes', async () => {
    const source = ref('a')
    const {vm, restore} = mountHost({scrollHeight: 200, lineHeight: 20, source})
    cleanups.push(restore)
    vm.update()
    vm.toggle()
    expect(vm.expanded).toBe(true)

    source.value = 'b'
    await nextTick()
    await nextTick()
    expect(vm.expanded).toBe(false)
  })
})
