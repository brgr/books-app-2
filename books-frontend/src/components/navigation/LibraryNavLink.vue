<script setup lang="ts">
import { type RouteLocationRaw, RouterLink } from "vue-router";
import { scrollToTop } from "../../utils/scrollToTop";

defineProps<{ label: string; active: boolean; to: RouteLocationRaw; scrollToTopOnClick?: boolean }>();

function handleClick(event: MouseEvent, reselected: boolean, navigate: (event: MouseEvent) => unknown) {
  // We want a plain click on the current tab to scroll to the top.
  // We call preventDefault() to stop navigation, but that also blocks browser
  // actions like Ctrl/Cmd-click to open a new tab. We therefore intercept only
  // primary-button clicks without modifiers, and we respect any earlier handler
  // that canceled the click.
  if (
    reselected &&
    !event.defaultPrevented &&
    event.button === 0 &&
    !event.metaKey &&
    !event.ctrlKey &&
    !event.shiftKey &&
    !event.altKey
  ) {
    event.preventDefault();
    scrollToTop();
    return;
  }

  void navigate(event);
}
</script>

<template>
  <RouterLink v-slot="{ href, navigate, isExactActive }" :to="to" custom>
    <a
      :href="href"
      :aria-current="active ? 'page' : undefined"
      :class="['nav-button', { active }]"
      @click="handleClick($event, isExactActive || scrollToTopOnClick, navigate)"
    >
      <slot name="icon" />
      <span class="nav-button-label">{{ label }}</span>
    </a>
  </RouterLink>
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
  text-decoration: none;
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
