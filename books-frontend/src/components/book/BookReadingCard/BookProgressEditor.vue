<script setup lang="ts">
import { ref } from "vue";
import type { ReadingProgress } from "./types";

type ProgressUnit = ReadingProgress["unit"];

const props = defineProps<{
  progress: ReadingProgress | null;
  pageCount?: number | null;
  isCurrentlySaving?: boolean;
}>();

const emit = defineEmits<{
  save: [progress: ReadingProgress];
  cancel: [];
}>();

const progressUnit = ref<ProgressUnit>(props.progress?.unit ?? "page");
const progressDraft = ref<string>(currentValueFor(progressUnit.value));

function currentValueFor(unit: ProgressUnit): string {
  return props.progress?.unit === unit ? props.progress.value.toString() : "";
}

function selectUnit(unit: ProgressUnit) {
  if (unit === progressUnit.value) {
    return;
  }

  progressUnit.value = unit;
  progressDraft.value = currentValueFor(unit);
}

function handleSaveProgress() {
  if (props.isCurrentlySaving) {
    return;
  }

  const trimmed = String(progressDraft.value ?? "").trim();
  if (!trimmed) {
    alert(progressUnit.value === "percent" ? "Please enter a percentage." : "Please enter a page number.");
    return;
  }
  if (progressUnit.value === "percent") {
    const percent = Number.parseFloat(trimmed);
    if (Number.isNaN(percent) || percent < 0 || percent > 100) {
      alert("Please enter a percentage between 0 and 100.");
      return;
    }
    emit("save", { unit: "percent", value: percent });
    return;
  }
  const page = Number.parseInt(trimmed, 10);
  if (Number.isNaN(page) || page < 0) {
    alert("Please enter a valid page number.");
    return;
  }
  emit("save", { unit: "page", value: page });
}

function handleProgressFocus(event: FocusEvent) {
  const target = event.target as HTMLInputElement | null;
  target?.select();
}
</script>

<template>
  <div class="progress-line">
    <span class="progress-edit">
      <span class="unit-toggle" role="group" aria-label="Progress unit">
        <button
          type="button"
          class="unit-btn"
          :class="{ active: progressUnit === 'page' }"
          data-test="unit-page"
          :disabled="isCurrentlySaving"
          @click="selectUnit('page')"
        >
          Page
        </button>
        <button
          type="button"
          class="unit-btn"
          :class="{ active: progressUnit === 'percent' }"
          data-test="unit-percent"
          :disabled="isCurrentlySaving"
          @click="selectUnit('percent')"
        >
          %
        </button>
      </span>
      <input
        v-model="progressDraft"
        type="number"
        min="0"
        :max="progressUnit === 'percent' ? 100 : undefined"
        :step="progressUnit === 'percent' ? 'any' : 1"
        inputmode="decimal"
        class="progress-input"
        data-test="progress-input"
        :aria-label="progressUnit === 'percent' ? 'Percentage read' : 'Current page'"
        :disabled="isCurrentlySaving"
        :placeholder="progressUnit === 'percent' ? '%' : 'Page'"
        @focus="handleProgressFocus"
      />
      <span class="muted progress-suffix">
        <template v-if="progressUnit === 'page' && pageCount">of {{ pageCount }}</template>
        <template v-else-if="progressUnit === 'percent'">%</template>
      </span>
      <button
        class="btn-link"
        type="button"
        data-test="save-progress"
        :disabled="isCurrentlySaving"
        @click="handleSaveProgress"
      >
        {{ isCurrentlySaving ? "Saving…" : "Save" }}
      </button>
      <button
        class="btn-link btn-link-cancel"
        type="button"
        data-test="cancel-progress"
        :disabled="isCurrentlySaving"
        @click="emit('cancel')"
      >
        Cancel
      </button>
    </span>
  </div>
</template>

<style scoped>
.muted {
  color: var(--color-text-secondary);
}

.progress-line,
.progress-edit {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  font-size: 0.9rem;
}

.unit-toggle {
  display: inline-flex;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.unit-btn {
  background: none;
  border: none;
  padding: 4px var(--spacing-sm);
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
}

.unit-btn:not(:last-child) {
  border-right: 1px solid var(--color-border);
}

.unit-btn.active {
  background: var(--color-primary);
  color: #fff;
}

.unit-btn:disabled {
  cursor: not-allowed;
}

/* Keep the editor's controls in place when switching progress units. */
.progress-suffix {
  min-width: 4rem;
  text-align: left;
}

.progress-input {
  width: 70px;
  padding: 4px var(--spacing-sm);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  appearance: textfield;
  -moz-appearance: textfield;
}

.progress-input::-webkit-outer-spin-button,
.progress-input::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.btn-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--color-primary);
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-link:hover:not(:disabled) {
  text-decoration: underline;
}

.btn-link:disabled {
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

.btn-link-cancel {
  color: var(--color-danger);
}
</style>
