<script setup lang="ts">
import ChevronRightIcon from "../icons/ChevronRightIcon.vue";

defineProps<{
  collapsed: boolean;
  /** Id of the element this button shows and hides. Needed for accessibility. */
  controls: string;
}>();
defineEmits<{ toggle: [] }>();
</script>

<template>
  <button
    type="button"
    class="shelf-collapse-toggle"
    :aria-expanded="!collapsed"
    :aria-controls="controls"
    @click="$emit('toggle')"
  >
    <slot />
    <ChevronRightIcon
      class="shelf-chevron"
      :class="{ expanded: !collapsed }"
      width="16"
      height="16"
      aria-hidden="true"
    />
  </button>
</template>

<style scoped>
.shelf-collapse-toggle {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-xs) 0;
  border: none;
  background: transparent;
  font: inherit;
  letter-spacing: inherit;
  text-transform: inherit;
  text-align: left;
}

.shelf-collapse-toggle:hover {
  background: transparent;
  color: var(--color-primary);
}

.shelf-collapse-toggle:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}

.shelf-chevron {
  flex-shrink: 0;
}

.shelf-chevron.expanded {
  transform: rotate(90deg);
}
</style>
