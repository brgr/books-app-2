<script setup lang="ts">
import { ref } from "vue";
import { ReadingDatePrecision, type ReadingDateValue } from "../../../../api/types";
import ConfirmButton from "../ConfirmButton.vue";

defineProps<{ actionLabel: string }>();
const emit = defineEmits<{ confirm: [readingDate: ReadingDateValue] }>();
const today = new Date().toISOString().slice(0, 10);
const chosenDate = ref(today);

function confirm() {
  if (!chosenDate.value) {
    return;
  }

  emit("confirm", {
    value: new Date(`${chosenDate.value}T12:00:00Z`).toISOString(),
    precision: ReadingDatePrecision.DAY,
  });
}
</script>

<template>
  <div class="precision-row">
    <input v-model="chosenDate" type="date" :max="today" class="date-input" data-test="shelf-date-input" />
    <ConfirmButton :disabled="!chosenDate" @click="confirm">
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
}
.date-input {
  padding: 6px 8px;
  border-radius: var(--border-radius);
  font: inherit;
  font-size: 0.9rem;
}
.date-input {
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
}
</style>
