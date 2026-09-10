<script setup lang="ts">
import { computed, ref } from "vue";
import { ReadingDatePrecision, type ReadingDateValue } from "../../../../api/types";
import ConfirmButton from "../ConfirmButton.vue";

defineProps<{ actionLabel: string }>();
const emit = defineEmits<{ confirm: [readingDate: ReadingDateValue] }>();

const today = new Date().toISOString().slice(0, 10);
const thisMonth = today.slice(0, 7);
const thisYear = today.slice(0, 4);
const monthNames = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];
const chosenMonth = ref(thisMonth.slice(5, 7));
const chosenYear = ref(thisYear);
const isValid = computed(() => {
  const year = Number(chosenYear.value);
  const month = Number(chosenMonth.value);
  return (
    Number.isInteger(year) &&
    year >= 1 &&
    year <= Number(thisYear) &&
    (year < Number(thisYear) || month <= Number(thisMonth.slice(5, 7)))
  );
});

function confirm() {
  if (!isValid.value) {
    return;
  }

  emit("confirm", {
    value: new Date(`${chosenYear.value}-${chosenMonth.value}-01T12:00:00Z`).toISOString(),
    precision: ReadingDatePrecision.MONTH,
  });
}
</script>

<template>
  <div class="precision-column">
    <div class="month-picker">
      <label class="sr-only" for="reading-date-month">Month</label>
      <select id="reading-date-month" v-model="chosenMonth" class="date-input" data-test="shelf-month-input">
        <option v-for="(monthName, index) in monthNames" :key="monthName" :value="String(index + 1).padStart(2, '0')">
          {{ monthName }}
        </option>
      </select>
      <label class="sr-only" for="reading-date-year">Year</label>
      <input
        id="reading-date-year"
        v-model="chosenYear"
        type="number"
        min="1"
        :max="thisYear"
        class="year-input"
        data-test="shelf-month-year-input"
        aria-label="Year"
      />
    </div>

    <ConfirmButton class="confirm-button" :disabled="!isValid" @click="confirm">
      {{ actionLabel }}
    </ConfirmButton>
  </div>
</template>

<style scoped>
.precision-column {
  display: flex;
  align-items: stretch;
  flex-direction: column;
  gap: 8px;
}
.month-picker {
  display: flex;
  gap: 6px;
}
.date-input {
  flex: 1;
}
.date-input,
.year-input {
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg);
  color: var(--color-text);
  font: inherit;
  font-size: 0.9rem;
}
.year-input {
  width: 5.5rem;
}
.confirm-button {
  align-self: flex-start;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
