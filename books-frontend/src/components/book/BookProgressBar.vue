<script setup lang="ts">
import {computed} from 'vue'

const props = defineProps<{
  currentPage?: number | null
  currentPercent?: number | null
  pageCount?: number | null
}>()

const hasPercent = computed(
  () => props.currentPercent !== null && props.currentPercent !== undefined,
)

const percent = computed(() => {
  if (hasPercent.value) {
    return Math.min(100, Math.max(0, Math.round(props.currentPercent as number)))
  }
  if (props.currentPage === null || props.currentPage === undefined || !props.pageCount) return 0
  return Math.min(100, Math.round((props.currentPage / props.pageCount) * 100))
})

// A concrete percentage is available whenever the user tracks by percent, or by
// page, and we know the book's length to derive one.
const showPercent = computed(() => hasPercent.value || Boolean(props.pageCount))
</script>

<template>
  <div class="bar-block">
    <div class="bar-track">
      <div class="bar-fill" :style="{width: percent + '%'}" />
    </div>
    <span class="bar-percent">{{ showPercent ? percent + '%' : '—' }}</span>
  </div>
</template>

<style scoped>
.bar-block {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  min-width: 260px;
}

.bar-track {
  flex: 1;
  height: 8px;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.1);
  overflow: hidden;
}

.bar-fill {
  height: 100%;
  border-radius: 999px;
  background: var(--color-primary);
  transition: width 240ms ease;
}

.bar-percent {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
  min-width: 3ch;
  text-align: right;
}
</style>
