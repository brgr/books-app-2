<script setup lang="ts">
defineProps<{ label: string; active: boolean }>();
defineEmits<{ select: [] }>();
</script>

<template>
  <button type="button" role="tab" :aria-selected="active" :class="['nav-button', { active }]" @click="$emit('select')">
    <slot name="icon" />
    <span class="nav-button-label">{{ label }}</span>
  </button>
</template>

<style scoped>
.nav-button {
  flex: 1 1 0;
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  gap: 3px;
  padding: 8px 6px;
  background: transparent;
  border: none;
  border-radius: 999px;
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition:
    background-color 0.15s ease,
    color 0.15s ease;
  user-select: none;
  -webkit-user-select: none;
  touch-action: manipulation;
}

.nav-button :slotted(svg) {
  width: 20px;
  height: 20px;
}

.nav-button-label {
  line-height: 1;
}

.nav-button:hover:not(.active) {
  color: var(--color-text);
}

.nav-button.active {
  background: color-mix(in srgb, var(--color-primary) 12%, transparent);
  color: var(--color-primary);
}

/* Desktop: the button becomes a quiet inline tab. */
@media (min-width: 769px) {
  .nav-button {
    flex: 0 0 auto;
    flex-direction: row;
    gap: 7px;
    padding: 8px 16px;
    font-size: 14px;
  }

  .nav-button :slotted(svg) {
    width: 16px;
    height: 16px;
  }
}
</style>
