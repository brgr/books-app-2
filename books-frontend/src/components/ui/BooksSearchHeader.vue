<script setup lang="ts">
const searchQuery = defineModel<string>("searchQuery", { required: true });
</script>

<template>
  <div class="search-header">
    <div class="search-bar">
      <svg
        class="search-icon"
        width="18"
        height="18"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        stroke-width="2"
        stroke-linecap="round"
        stroke-linejoin="round"
      >
        <circle cx="11" cy="11" r="8"></circle>
        <path d="m21 21-4.35-4.35"></path>
      </svg>
      <input v-model="searchQuery" type="text" placeholder="Search for words or #tags" class="search-input" />
    </div>
  </div>
</template>

<style scoped>
.search-header {
  display: flex;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-lg);
  padding: var(--spacing-md);
  align-items: center;
  border-radius: var(--border-radius);
  max-width: 100%;
  overflow: visible;
}

.search-bar {
  flex: 1 1 auto;
  min-width: 0;
  max-width: 500px;
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  padding: var(--spacing-sm) var(--spacing-lg);
  background-color: rgba(255, 255, 255, 0.04);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  transition:
    border-color 0.15s ease,
    box-shadow 0.15s ease;
}

.search-bar:hover {
  border-color: var(--color-text-secondary);
}

.search-bar:focus-within {
  border-color: var(--color-primary);
  box-shadow: 0 0 0 1px rgba(88, 86, 214, 0.35);
}

.search-icon {
  color: var(--color-text-secondary);
  flex-shrink: 0;
}

.search-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 0;
  font-size: 14px;
}

.search-input:focus {
  outline: none;
  border: none;
}

@media (max-width: 768px) {
  .search-bar {
    max-width: 100%;
  }

  /* Prevent iOS Safari zooming inputs with font-size under 16px. */
  .search-input {
    font-size: 16px;
  }
}
</style>
