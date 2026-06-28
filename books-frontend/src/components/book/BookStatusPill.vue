<script setup lang="ts">
import {computed, onBeforeUnmount, onMounted, ref} from 'vue'
import {ReadingStatus} from '../../api/types'

const props = defineProps<{
  status: ReadingStatus | null
  updating: boolean
}>()

const emit = defineEmits<{
  change: [status: ReadingStatus]
}>()

const open = ref(false)
const root = ref<HTMLElement | null>(null)

const currentStatus = computed(() => props.status ?? ReadingStatus.WANT_TO_READ)

type Option = {value: ReadingStatus; label: string}
const options: readonly [Option, Option, Option] = [
  {value: ReadingStatus.WANT_TO_READ, label: 'Want to read'},
  {value: ReadingStatus.STARTED, label: 'Reading'},
  {value: ReadingStatus.FINISHED, label: 'Finished'},
]

const currentOption = computed<Option>(
  () => options.find((o) => o.value === currentStatus.value) ?? options[0],
)

function toggle() {
  if (props.updating) return
  open.value = !open.value
}

function pick(status: ReadingStatus) {
  open.value = false
  if (status === currentStatus.value) return
  emit('change', status)
}

function handleDocumentClick(e: MouseEvent) {
  if (!root.value) return
  if (!root.value.contains(e.target as Node)) open.value = false
}

function handleKey(e: KeyboardEvent) {
  if (e.key === 'Escape') open.value = false
}

onMounted(() => {
  document.addEventListener('click', handleDocumentClick)
  document.addEventListener('keydown', handleKey)
})
onBeforeUnmount(() => {
  document.removeEventListener('click', handleDocumentClick)
  document.removeEventListener('keydown', handleKey)
})
</script>

<template>
  <div ref="root" class="status-pill-wrap" data-test="status-pill">
    <button
      type="button"
      class="status-pill"
      :class="`status-${currentStatus}`"
      :disabled="updating"
      :aria-haspopup="'menu'"
      :aria-expanded="open"
      data-test="status-pill-button"
      @click="toggle"
    >
      <span class="pill-label">{{ currentOption.label }}</span>
      <span class="pill-caret" aria-hidden="true">▾</span>
    </button>
    <ul v-if="open" class="status-menu" role="menu" data-test="status-menu">
      <li v-for="opt in options" :key="opt.value" role="none">
        <button
          type="button"
          role="menuitem"
          class="menu-item"
          :class="{active: opt.value === currentStatus}"
          :data-test="`status-option-${opt.value}`"
          @click="pick(opt.value)"
        >
          <span>{{ opt.label }}</span>
          <span v-if="opt.value === currentStatus" class="check" aria-hidden="true">•</span>
        </button>
      </li>
    </ul>
  </div>
</template>

<style scoped>
.status-pill-wrap {
  position: relative;
  display: inline-block;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: 4px 10px 4px 8px;
  border-radius: 999px;
  border: 1px solid var(--color-border);
  background: rgba(255, 255, 255, 0.04);
  color: var(--color-text);
  font-size: 0.85rem;
  font-family: inherit;
  cursor: pointer;
  line-height: 1.2;
}

.status-pill:hover:not(:disabled) {
  background: rgba(255, 255, 255, 0.08);
}

.status-pill:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.pill-caret {
  font-size: 0.7rem;
  color: var(--color-text-secondary);
}

.status-menu {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  z-index: 10;
  margin: 0;
  padding: 4px;
  list-style: none;
  background: var(--color-bg-card, #1a1520);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
  min-width: 180px;
}

.menu-item {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  width: 100%;
  padding: 6px 10px;
  border: none;
  background: none;
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.9rem;
  text-align: left;
  border-radius: var(--radius-sm, 4px);
  cursor: pointer;
}

.menu-item:hover {
  background: rgba(255, 255, 255, 0.08);
}

.menu-item.active {
  color: var(--color-primary);
}

.check {
  margin-left: auto;
  font-size: 0.85rem;
}
</style>
