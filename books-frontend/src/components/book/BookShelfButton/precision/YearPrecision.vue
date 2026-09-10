<script setup lang="ts">
import { computed, ref } from "vue";
import { ReadingDatePrecision, type ReadingDateValue } from "../../../../api/types";
import ConfirmButton from "../ConfirmButton.vue";

defineProps<{ actionLabel: string }>();
const emit = defineEmits<{ confirm: [readingDate: ReadingDateValue] }>();
const thisYear = new Date().toISOString().slice(0, 4);
const chosenYear = ref(thisYear);
const validationMessage = computed(() => {
  if (!chosenYear.value) {
    return "Enter a year.";
  }

  const year = Number(chosenYear.value);
  if (!Number.isInteger(year)) {
    return "Enter a whole year.";
  }

  if (year < 1900 || year > Number(thisYear)) {
    return `Enter a year from 1900 to ${thisYear}.`;
  }

  return null;
});
const isValid = computed(() => validationMessage.value === null);

function confirm() {
  if (!isValid.value) {
    return;
  }

  const year = String(Number(chosenYear.value)).padStart(4, "0");

  emit("confirm", {
    value: new Date(`${year}-01-01T12:00:00Z`).toISOString(),
    precision: ReadingDatePrecision.YEAR,
  });
}
</script>

<template>
  <div class="precision-column">
    <div class="precision-row">
      <input
        v-model="chosenYear"
        type="number"
        min="1"
        :max="thisYear"
        class="date-input"
        data-test="shelf-date-input"
        :aria-invalid="!isValid"
        :aria-describedby="isValid ? undefined : 'reading-year-error'"
      />
      <ConfirmButton :disabled="!isValid" @click="confirm">
        {{ actionLabel }}
      </ConfirmButton>
    </div>
    <p
      v-if="validationMessage"
      id="reading-year-error"
      class="validation-message"
      data-test="shelf-date-error"
      aria-live="polite"
    >
      {{ validationMessage }}
    </p>
  </div>
</template>

<style scoped>
.precision-column {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.precision-row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.date-input {
  flex: 1;
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg);
  color: var(--color-text);
  font: inherit;
  font-size: 0.9rem;
}
.validation-message {
  margin: 0;
  color: var(--color-danger);
  font-size: 0.8rem;
}
</style>
