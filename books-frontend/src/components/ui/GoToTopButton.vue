<script setup lang="ts">
import { onActivated, onBeforeUnmount, onDeactivated, onMounted, ref } from "vue";
import { scrollToTop } from "../../utils/scrollToTop";

const visible = ref(false);

function updateVisibility() {
  visible.value = window.scrollY > window.innerHeight;
}

function listen() {
  updateVisibility();
  window.addEventListener("scroll", updateVisibility, { passive: true });
  window.addEventListener("resize", updateVisibility);
}

function stop() {
  window.removeEventListener("scroll", updateVisibility);
  window.removeEventListener("resize", updateVisibility);
}

onMounted(listen);
onActivated(listen);
onDeactivated(stop);
onBeforeUnmount(stop);
</script>

<template>
  <button v-if="visible" type="button" class="go-to-top" @click="scrollToTop">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="m6 12 6-6 6 6M12 6v14" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
    Go to top
  </button>
</template>

<style scoped>
.go-to-top {
  position: fixed;
  right: var(--spacing-md);
  bottom: calc(96px + env(safe-area-inset-bottom));
  z-index: 40;
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-height: 44px;
  border-radius: 999px;
  box-shadow: var(--modal-shadow);
  color: var(--color-primary);
}

.go-to-top svg {
  width: 20px;
  height: 20px;
}

@media (min-width: 769px) {
  .go-to-top {
    right: var(--spacing-lg);
    bottom: var(--spacing-lg);
  }
}
</style>
