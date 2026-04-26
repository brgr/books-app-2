import {ref, onMounted, onBeforeUnmount, watch, nextTick, type Ref} from 'vue'

export interface UseClampToggleOptions {
  lines?: number
  source?: Ref<unknown>
}

export function useClampToggle(
  elementRef: Ref<HTMLElement | null>,
  options: UseClampToggleOptions = {},
) {
  const lines = options.lines ?? 3
  const expanded = ref(false)
  const showToggle = ref(false)
  const maxHeight = ref<string>('')

  function getClampHeight(el: HTMLElement) {
    const styles = window.getComputedStyle(el)
    const lineHeight = parseFloat(styles.lineHeight)
    if (Number.isFinite(lineHeight)) {
      return Math.round(lineHeight * lines)
    }
    const fontSize = parseFloat(styles.fontSize) || 16
    return Math.round(fontSize * 1.6 * lines)
  }

  function measureExpandedHeight(el: HTMLElement) {
    const previous = {overflow: el.style.overflow, maxHeight: el.style.maxHeight}
    el.style.overflow = 'visible'
    el.style.maxHeight = 'none'
    const height = el.scrollHeight
    el.style.overflow = previous.overflow
    el.style.maxHeight = previous.maxHeight
    return height
  }

  function update() {
    const el = elementRef.value
    if (!el) {
      showToggle.value = false
      return
    }
    const clampHeight = getClampHeight(el)
    showToggle.value = el.scrollHeight > clampHeight + 1
    maxHeight.value = expanded.value
      ? `${measureExpandedHeight(el)}px`
      : `${clampHeight}px`
  }

  function toggle() {
    const el = elementRef.value
    if (!el) return
    const clampHeight = getClampHeight(el)
    if (!expanded.value) {
      const expandedHeight = measureExpandedHeight(el)
      maxHeight.value = `${clampHeight}px`
      void el.offsetHeight
      maxHeight.value = `${expandedHeight}px`
      expanded.value = true
      return
    }
    const currentHeight = measureExpandedHeight(el)
    maxHeight.value = `${currentHeight}px`
    void el.offsetHeight
    maxHeight.value = `${clampHeight}px`
    expanded.value = false
  }

  onMounted(() => {
    window.addEventListener('resize', update)
  })

  onBeforeUnmount(() => {
    window.removeEventListener('resize', update)
  })

  if (options.source) {
    watch(options.source, async () => {
      expanded.value = false
      await nextTick()
      update()
    })
  }

  return {expanded, showToggle, maxHeight, update, toggle}
}
