<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { type ReadingDateValue, ReadingShelf } from "../../../api/types";
import ReadingDateMenu from "./ReadingDateMenu.vue";

const props = defineProps<{
  shelf: ReadingShelf | null;
  updating: boolean;
}>();

const emit = defineEmits<{
  change: [shelf: ReadingShelf, readingDate?: ReadingDateValue];
}>();

type Action = { label: string; target: ReadingShelf };

const action = computed<Action>(() => {
  switch (props.shelf) {
    case ReadingShelf.STARTED:
      return { label: "Finish", target: ReadingShelf.FINISHED };
    case ReadingShelf.FINISHED:
      return { label: "Read Again", target: ReadingShelf.STARTED };
    default:
      return { label: "Start Reading", target: ReadingShelf.STARTED };
  }
});

const dateLabel = computed(() =>
  action.value.target === ReadingShelf.FINISHED ? "When did you finish?" : "When did you start?",
);

const menuOpen = ref(false);
const rootEl = ref<HTMLElement | null>(null);

function activate() {
  if (!props.updating) emit("change", action.value.target);
}

function toggleMenu() {
  if (!props.updating) menuOpen.value = !menuOpen.value;
}

function closeMenu() {
  menuOpen.value = false;
}

function confirmDate(readingDate: ReadingDateValue) {
  if (props.updating) return;
  emit("change", action.value.target, readingDate);
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

    <ReadingDateMenu v-if="menuOpen" :date-label="dateLabel" :action-label="action.label" @confirm="confirmDate" />
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
.shelf-button,
.shelf-caret {
  display: inline-flex;
  align-items: center;
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: #fff;
  font: 500 0.9rem inherit;
  cursor: pointer;
  line-height: 1.2;
}
.shelf-button {
  padding: 8px 16px;
  border-radius: 999px 0 0 999px;
}
.shelf-caret {
  padding: 8px 12px;
  border-radius: 0 999px 999px 0;
  border-left-color: rgba(255, 255, 255, 0.4);
}
.shelf-button:hover:not(:disabled),
.shelf-caret:hover:not(:disabled) {
  filter: brightness(1.1);
}
.shelf-button:disabled,
.shelf-caret:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
