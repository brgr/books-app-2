<script setup lang="ts">
import { computed, ref } from "vue";
import { type ReadingDateValue, ReadingDatePrecision } from "../../../api/types";
import DayPrecision from "./precision/DayPrecision.vue";
import MonthPrecision from "./precision/MonthPrecision.vue";
import UnknownPrecision from "./precision/UnknownPrecision.vue";
import YearPrecision from "./precision/YearPrecision.vue";

defineProps<{ dateLabel: string; actionLabel: string }>();
const emit = defineEmits<{ confirm: [readingDate: ReadingDateValue] }>();

const precision = ref<ReadingDatePrecision>(ReadingDatePrecision.DAY);
const precisionComponent = computed(() => {
  switch (precision.value) {
    case ReadingDatePrecision.MONTH:
      return MonthPrecision;
    case ReadingDatePrecision.YEAR:
      return YearPrecision;
    case ReadingDatePrecision.UNKNOWN:
      return UnknownPrecision;
    default:
      return DayPrecision;
  }
});
</script>

<template>
  <div class="shelf-menu" role="dialog" :aria-label="dateLabel">
    <label class="shelf-menu-label">{{ dateLabel }}</label>
    <label class="shelf-menu-label" for="reading-date-precision">Date precision</label>
    <select
      id="reading-date-precision"
      v-model="precision"
      class="shelf-precision-select"
      data-test="shelf-date-precision"
    >
      <option :value="ReadingDatePrecision.DAY">Exact day</option>
      <option :value="ReadingDatePrecision.MONTH">Month</option>
      <option :value="ReadingDatePrecision.YEAR">Year</option>
      <option :value="ReadingDatePrecision.UNKNOWN">Unknown</option>
    </select>
    <component
      :is="precisionComponent"
      :key="precision"
      :action-label="actionLabel"
      @confirm="emit('confirm', $event)"
    />
  </div>
</template>

<style scoped>
.shelf-menu {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  z-index: 1000;
  min-width: 240px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: 0 12px 30px rgba(0, 0, 0, 0.2);
}
.shelf-menu-label {
  font-size: 0.85rem;
  color: var(--color-text-secondary);
}
.shelf-precision-select {
  padding: 6px 8px;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg);
  color: var(--color-text);
  font: 0.9rem inherit;
}
</style>
