<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ShelfName } from "../../api/types";

const props = defineProps<{
  shelf: ShelfName | null;
  updating: boolean;
}>();

const emit = defineEmits<{
  change: [shelf: ShelfName, occurredAt?: string];
}>();

type Action = { label: string; target: ShelfName };

// The single next action for the current shelf. Not-yet-started and abandoned
// books both offer "Start Reading"; a finished book can be read again.
const action = computed<Action>(() => {
  switch (props.shelf) {
    case ShelfName.STARTED:
      return { label: "Finish", target: ShelfName.FINISHED };
    case ShelfName.FINISHED:
      return { label: "Read Again", target: ShelfName.STARTED };
    default:
      return { label: "Start Reading", target: ShelfName.STARTED };
  }
});

const pastDateLabel = computed(() =>
  action.value.target === ShelfName.FINISHED ? "Finish on a past date…" : "Start on a past date…",
);

// Today in the input's yyyy-mm-dd format, used to bar future dates client-side
// (the backend rejects them too).
const today = new Date().toISOString().slice(0, 10);

const menuOpen = ref(false);
const chosenDate = ref("");
const rootEl = ref<HTMLElement | null>(null);

function activate() {
  if (props.updating) return;
  emit("change", action.value.target); // one-tap = now
}

function toggleMenu() {
  if (props.updating) return;
  menuOpen.value = !menuOpen.value;
  if (menuOpen.value) chosenDate.value = today;
}

function closeMenu() {
  menuOpen.value = false;
}

function confirmDate() {
  if (props.updating || !chosenDate.value) return;
  // Anchor at local noon so the calendar date survives the conversion to a UTC
  // instant, then hand the backend a full ISO datetime.
  const occurredAt = new Date(`${chosenDate.value}T12:00:00`).toISOString();
  emit("change", action.value.target, occurredAt);
  closeMenu();
}

function onDocPointer(e: PointerEvent) {
  if (rootEl.value && !rootEl.value.contains(e.target as Node)) closeMenu();
}

function onKey(e: KeyboardEvent) {
  if (e.key === "Escape") closeMenu();
}

onMounted(() => {
  document.addEventListener("pointerdown", onDocPointer);
  document.addEventListener("keydown", onKey);
});

onBeforeUnmount(() => {
  document.removeEventListener("pointerdown", onDocPointer);
  document.removeEventListener("keydown", onKey);
});
</script>

<template>
  <div ref="rootEl" class="shelf-control">
    <div class="shelf-split">
      <button type="button" class="shelf-button" :disabled="updating" data-test="shelf-button" @click="activate">
        {{ updating ? "Saving…" : action.label }}
      </button>
      <button
        type="button"
        class="shelf-caret"
        :disabled="updating"
        :aria-expanded="menuOpen"
        aria-label="Choose a date"
        data-test="shelf-caret"
        @click="toggleMenu"
      >
        ▾
      </button>
    </div>

    <div v-if="menuOpen" class="shelf-menu" role="dialog" :aria-label="pastDateLabel">
      <label class="shelf-menu-label">{{ pastDateLabel }}</label>
      <div class="shelf-menu-row">
        <input v-model="chosenDate" type="date" :max="today" class="shelf-date-input" data-test="shelf-date-input" />
        <button
          type="button"
          class="shelf-button"
          :disabled="updating || !chosenDate"
          data-test="shelf-date-confirm"
          @click="confirmDate"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.shelf-control {
  position: relative;
  align-self: flex-start;
}

.shelf-split {
  display: inline-flex;
}

.shelf-button {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.9rem;
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  line-height: 1.2;
}

.shelf-button:hover:not(:disabled) {
  filter: brightness(1.1);
}

.shelf-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* The caret shares the pill with the main button: round only the outer
   corners of each so the two read as one control. */
.shelf-split .shelf-button {
  border-radius: 999px 0 0 999px;
}

.shelf-caret {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border-radius: 0 999px 999px 0;
  border: 1px solid var(--color-primary);
  border-left-color: rgba(255, 255, 255, 0.4);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.9rem;
  font-family: inherit;
  cursor: pointer;
  line-height: 1.2;
}

.shelf-caret:hover:not(:disabled) {
  filter: brightness(1.1);
}

.shelf-caret:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.shelf-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 1000;
  min-width: 240px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.shelf-menu-label {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.shelf-menu-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.shelf-date-input {
  flex: 1;
  padding: 6px 8px;
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.9rem;
}
</style>
