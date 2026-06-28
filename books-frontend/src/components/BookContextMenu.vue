<script setup lang="ts">
import { ref, watch, onMounted, onBeforeUnmount, nextTick } from 'vue'

const props = defineProps<{
  x: number
  y: number
}>()

const emit = defineEmits<{
  (e: 'view'): void
  (e: 'close'): void
}>()

const menuEl = ref<HTMLElement | null>(null)
const pos = ref({ top: props.y, left: props.x })

function clamp() {
  const el = menuEl.value
  if (!el) return
  const rect = el.getBoundingClientRect()
  const margin = 8
  let left = props.x
  let top = props.y
  if (left + rect.width + margin > window.innerWidth) {
    left = window.innerWidth - rect.width - margin
  }
  if (top + rect.height + margin > window.innerHeight) {
    top = window.innerHeight - rect.height - margin
  }
  pos.value = { top: Math.max(margin, top), left: Math.max(margin, left) }
}

function onKey(e: KeyboardEvent) {
  if (e.key === 'Escape') emit('close')
}

watch(
  () => [props.x, props.y],
  () => nextTick(clamp)
)

onMounted(() => {
  nextTick(clamp)
  document.addEventListener('keydown', onKey)
})

onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKey)
})
</script>

<template>
  <teleport to="body">
    <div
      class="ctx-backdrop"
      @click="emit('close')"
      @contextmenu.prevent="emit('close')"
    >
      <div
        ref="menuEl"
        class="ctx-menu"
        role="menu"
        :style="{ top: pos.top + 'px', left: pos.left + 'px' }"
        @click.stop
      >
        <button
          type="button"
          class="ctx-item"
          role="menuitem"
          @click="emit('view')"
        >
          View Book
        </button>
      </div>
    </div>
  </teleport>
</template>

<style scoped>
.ctx-backdrop {
  position: fixed;
  inset: 0;
  z-index: 1000;
}

.ctx-menu {
  position: fixed;
  min-width: 168px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
  padding: 6px 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

.ctx-item {
  width: 100%;
  text-align: left;
  background: transparent;
  border: none;
  padding: 10px 12px;
  font-size: 0.95rem;
  font-weight: 500;
  color: var(--color-text);
  cursor: pointer;
  transition: background 0.12s ease;
}

.ctx-item:hover,
.ctx-item:focus-visible {
  background: var(--color-bg);
  outline: none;
}
</style>
