<script setup lang="ts">
import { ref } from "vue";
import { ReadingDatePrecision, type ReadingDateValue } from "../../../../api/types";
import ConfirmButton from "../ConfirmButton.vue";

defineProps<{ actionLabel: string }>();
const emit = defineEmits<{ confirm: [readingDate: ReadingDateValue] }>();
const thisYear = new Date().toISOString().slice(0, 4);
const chosenYear = ref(thisYear);

function confirm() {
  if (!chosenYear.value) return;

  emit("confirm", {
    value: new Date(`${chosenYear.value}-01-01T12:00:00Z`).toISOString(),
    precision: ReadingDatePrecision.YEAR,
  });
}
</script>

<template>
  <div class="precision-row">
    <input v-model="chosenYear" type="number" min="1" :max="thisYear" class="date-input" data-test="shelf-date-input" />
    <ConfirmButton :disabled="!chosenYear" @click="confirm">
      {{ actionLabel }}
    </ConfirmButton>
  </div>
</template>

<style scoped>
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
</style>
