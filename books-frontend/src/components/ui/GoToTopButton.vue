<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import { pageScroller } from "../../utils/pageScroller";
import { scrollToTop } from "../../utils/scrollToTop";

const visible = ref(false);
let scroller: HTMLElement | null = null;

function updateVisibility() {
  visible.value = scroller !== null && scroller.scrollTop > scroller.clientHeight;
}

function listen() {
  scroller = pageScroller();
  updateVisibility();
  scroller?.addEventListener("scroll", updateVisibility, { passive: true });
  window.addEventListener("resize", updateVisibility);
}

function stop() {
  scroller?.removeEventListener("scroll", updateVisibility);
  window.removeEventListener("resize", updateVisibility);
}

onMounted(listen);
onBeforeUnmount(stop);
</script>

<template>
  <button v-if="visible" type="button" class="go-to-top" aria-label="Go to top" title="Go to top" @click="scrollToTop">
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">
      <path d="m6 12 6-6 6 6M12 6v14" stroke-linecap="round" stroke-linejoin="round" />
    </svg>
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
  justify-content: center;
  width: 40px;
  height: 40px;
  padding: 0;
  border-radius: 50%;
  box-shadow: var(--modal-shadow);
  color: var(--color-primary);
}

.go-to-top svg {
  width: 18px;
  height: 18px;
}

@media (min-width: 769px) {
  .go-to-top {
    right: var(--spacing-lg);
    bottom: var(--spacing-lg);
  }
}
</style>
