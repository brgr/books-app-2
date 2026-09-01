<script setup lang="ts">
import { ReadingDatePrecision, type ReadingDateValue } from "../../../../api/types";
import ConfirmButton from "../ConfirmButton.vue";

defineProps<{ actionLabel: string }>();
const emit = defineEmits<{ confirm: [readingDate: ReadingDateValue] }>();
</script>

<template>
  <div class="precision-row">
    <ConfirmButton @click="emit('confirm', { value: null, precision: ReadingDatePrecision.UNKNOWN })">
      {{ actionLabel }}
    </ConfirmButton>
  </div>
</template>

<style scoped>
.precision-row {
  display: flex;
}
</style>
