<script setup lang="ts">
defineProps<{
  disabled?: boolean;
}>();

const emit = defineEmits<{ click: [] }>();
</script>

<template>
  <button
    type="button"
    class="confirm-button"
    :disabled="disabled"
    data-test="shelf-date-confirm"
    @click="emit('click')"
  >
    <slot />
  </button>
</template>

<style scoped>
.confirm-button {
  padding: 6px 8px;
  border: 1px solid var(--color-primary);
  border-radius: var(--border-radius);
  background: var(--color-primary);
  color: #fff;
  font: inherit;
  font-size: 0.9rem;
  cursor: pointer;
}
.confirm-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
