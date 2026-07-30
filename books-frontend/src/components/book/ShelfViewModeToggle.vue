<script setup lang="ts">
const viewMode = defineModel<"list" | "grid">({ required: true });
</script>

<template>
  <div class="view-toggle">
    <button @click="viewMode = 'list'" :class="['view-btn', { active: viewMode === 'list' }]" title="List view">
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <line x1="8" y1="6" x2="21" y2="6"></line>
        <line x1="8" y1="12" x2="21" y2="12"></line>
        <line x1="8" y1="18" x2="21" y2="18"></line>
        <line x1="3" y1="6" x2="3.01" y2="6"></line>
        <line x1="3" y1="12" x2="3.01" y2="12"></line>
        <line x1="3" y1="18" x2="3.01" y2="18"></line>
      </svg>
    </button>

    <button @click="viewMode = 'grid'" :class="['view-btn', { active: viewMode === 'grid' }]" title="Grid view">
      <svg
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <rect x="3" y="3" width="7" height="7"></rect>
        <rect x="14" y="3" width="7" height="7"></rect>
        <rect x="14" y="14" width="7" height="7"></rect>
        <rect x="3" y="14" width="7" height="7"></rect>
      </svg>
    </button>
  </div>
</template>

<style scoped>
.view-toggle {
  display: flex;
  gap: 0;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  overflow: hidden;
  background-color: var(--color-bg-card);
}

.view-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--spacing-xs) var(--spacing-sm);
  background: transparent;
  border: none;
  cursor: pointer;
  color: var(--color-text-secondary);
  transition: all 0.15s ease;
  min-width: 34px;
  min-height: 30px;
  position: relative;
}

.view-btn:not(:last-child)::after {
  content: "";
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  height: 60%;
  width: 1px;
  background-color: var(--color-border);
}

.view-btn:hover:not(.active) {
  color: var(--color-text);
  background-color: var(--color-bg);
}

.view-btn.active {
  background-color: var(--color-primary);
  color: white;
}

.view-btn.active::after {
  display: none;
}

.view-btn.active:hover {
  background-color: var(--color-primary-hover);
  color: white;
}
</style>
