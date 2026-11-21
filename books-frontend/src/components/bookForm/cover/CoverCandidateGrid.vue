<template>
  <div class="cover-grid">
    <slot />
  </div>
</template>

<style scoped>
.cover-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--spacing-md);
  max-height: 60vh;
  overflow-y: auto;
}
</style>
