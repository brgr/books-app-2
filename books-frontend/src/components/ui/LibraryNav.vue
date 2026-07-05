<script setup lang="ts">
import LibraryNavButton from "./LibraryNavButton.vue";

const surface = defineModel<"to-read" | "finished">({ required: true });
</script>

<template>
  <nav class="library-nav" role="tablist" aria-label="Library">
    <LibraryNavButton label="To Read" :active="surface === 'to-read'" @select="surface = 'to-read'">
      <template #icon>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M2 6.5A2.5 2.5 0 0 1 4.5 4H10a2 2 0 0 1 2 2v13a1.5 1.5 0 0 0-1.5-1.5H4.5A2.5 2.5 0 0 1 2 15V6.5z" />
          <path d="M22 6.5A2.5 2.5 0 0 0 19.5 4H14a2 2 0 0 0-2 2v13a1.5 1.5 0 0 1 1.5-1.5h6A2.5 2.5 0 0 0 22 15V6.5z" />
        </svg>
      </template>
    </LibraryNavButton>

    <LibraryNavButton label="Finished" :active="surface === 'finished'" @select="surface = 'finished'">
      <template #icon>
        <svg
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="1.8"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <rect x="4" y="3" width="4" height="18" rx="1" />
          <rect x="10" y="3" width="4" height="18" rx="1" />
          <path d="M17 4.2l3.2.9-3 14.6-3.2-.9" />
        </svg>
      </template>
    </LibraryNavButton>
  </nav>
</template>

<style scoped>
/* Mobile: a floating bottom bar within thumb reach. */
.library-nav {
  position: fixed;
  left: 50%;
  bottom: calc(14px + env(safe-area-inset-bottom));
  transform: translateX(-50%);
  width: min(92vw, 420px);
  display: flex;
  gap: 6px;
  padding: 6px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: 999px;
  box-shadow: var(--modal-shadow);
  z-index: 30;
}

/* Desktop: the same two buttons become inline tabs in the header. */
@media (min-width: 769px) {
  .library-nav {
    position: static;
    transform: none;
    width: auto;
    justify-content: flex-start;
    gap: 4px;
    padding: 0;
    margin: 0;
    background: transparent;
    border: none;
    border-radius: 0;
    box-shadow: none;
  }
}
</style>
