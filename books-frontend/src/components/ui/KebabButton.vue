<template>
  <button type="button" class="kebab-button">
    <svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true">
      <circle cx="5" cy="12" r="2" />
      <circle cx="12" cy="12" r="2" />
      <circle cx="19" cy="12" r="2" />
    </svg>
  </button>
</template>

<style scoped>
.kebab-button {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  padding: 0;
  background: transparent;
  border: none;
  border-radius: 2px;
  color: var(--color-text-secondary);
  cursor: pointer;
  transition: background 0.15s ease, color 0.15s ease;
}

.kebab-button:hover,
.kebab-button:focus-visible {
  background: var(--color-bg);
  color: var(--color-text);
  outline: none;
}

.kebab-button svg {
  fill: currentColor;
}
</style>
