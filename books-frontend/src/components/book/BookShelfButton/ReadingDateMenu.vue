<script setup lang="ts">
import { computed, ref } from "vue";
import { ReadingDatePrecision, type ReadingDateValue } from "../../../api/types";
import DayPrecision from "./precision/DayPrecision.vue";
import MonthPrecision from "./precision/MonthPrecision.vue";
import UnknownPrecision from "./precision/UnknownPrecision.vue";
import YearPrecision from "./precision/YearPrecision.vue";

defineProps<{ dateLabel: string; actionLabel: string; showPause?: boolean; showAbandon?: boolean }>();
const emit = defineEmits<{
  confirm: [readingDate: ReadingDateValue];
  pause: [];
  abandon: [];
}>();

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
    <button v-if="showPause" type="button" class="pause-action" data-test="pause-reading" @click="emit('pause')">
      Pause Reading
    </button>

    <button
      v-if="showAbandon"
      type="button"
      class="abandon-action"
      data-test="abandon-reading"
      @click="emit('abandon')"
    >
      Abandon Book
    </button>

    <div v-if="showPause || showAbandon" class="menu-divider" aria-hidden="true"></div>

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
.pause-action,
.abandon-action {
  padding: 7px 8px;
  border: 0;
  border-radius: var(--border-radius);
  background: transparent;
  color: var(--color-text);
  font: 500 0.9rem inherit;
  text-align: left;
  cursor: pointer;
}
.pause-action:hover,
.abandon-action:hover {
  background: var(--color-bg);
}
.menu-divider {
  height: 1px;
  background: var(--color-border);
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
