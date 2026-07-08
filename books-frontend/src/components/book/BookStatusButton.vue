<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { ReadingStatus } from "../../api/types";

const props = defineProps<{
  status: ReadingStatus | null;
  updating: boolean;
}>();

const emit = defineEmits<{
  change: [status: ReadingStatus, occurredAt?: string];
}>();

type Action = { label: string; target: ReadingStatus };

// The single next action for the current status. Not-yet-started and abandoned
// books both offer "Start Reading"; a finished book can be read again.
const action = computed<Action>(() => {
  switch (props.status) {
    case ReadingStatus.STARTED:
      return { label: "Finish", target: ReadingStatus.FINISHED };
    case ReadingStatus.FINISHED:
      return { label: "Read Again", target: ReadingStatus.STARTED };
    default:
      return { label: "Start Reading", target: ReadingStatus.STARTED };
  }
});

const pastDateLabel = computed(() =>
  action.value.target === ReadingStatus.FINISHED ? "Finish on a past date…" : "Start on a past date…",
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
  <div ref="rootEl" class="status-control">
    <div class="status-split">
      <button type="button" class="status-button" :disabled="updating" data-test="status-button" @click="activate">
        {{ updating ? "Saving…" : action.label }}
      </button>
      <button
        type="button"
        class="status-caret"
        :disabled="updating"
        :aria-expanded="menuOpen"
        aria-label="Choose a date"
        data-test="status-caret"
        @click="toggleMenu"
      >
        ▾
      </button>
    </div>

    <div v-if="menuOpen" class="status-menu" role="dialog" :aria-label="pastDateLabel">
      <label class="status-menu-label">{{ pastDateLabel }}</label>
      <div class="status-menu-row">
        <input v-model="chosenDate" type="date" :max="today" class="status-date-input" data-test="status-date-input" />
        <button
          type="button"
          class="status-button"
          :disabled="updating || !chosenDate"
          data-test="status-date-confirm"
          @click="confirmDate"
        >
          {{ action.label }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.status-control {
  position: relative;
  align-self: flex-start;
}

.status-split {
  display: inline-flex;
}

.status-button {
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

.status-button:hover:not(:disabled) {
  filter: brightness(1.1);
}

.status-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* The caret shares the pill with the main button: round only the outer
   corners of each so the two read as one control. */
.status-split .status-button {
  border-radius: 999px 0 0 999px;
}

.status-caret {
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

.status-caret:hover:not(:disabled) {
  filter: brightness(1.1);
}

.status-caret:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.status-menu {
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

.status-menu-label {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}

.status-menu-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-date-input {
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
