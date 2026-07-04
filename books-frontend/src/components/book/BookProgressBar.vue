<script setup lang="ts">
import {computed} from 'vue'

const props = defineProps<{
  currentPage?: number | null
  pageCount?: number | null
}>()

const percent = computed(() => {
  if (props.currentPage === null || props.currentPage === undefined || !props.pageCount) return 0
  return Math.min(100, Math.round((props.currentPage / props.pageCount) * 100))
})
</script>

<template>
  <div class="bar-block">
    <div class="bar-track">
      <div class="bar-fill" :style="{width: percent + '%'}" />
    </div>
    <span class="bar-percent">{{ pageCount ? percent + '%' : '—' }}</span>
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
