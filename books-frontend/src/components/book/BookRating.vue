<script setup lang="ts">
defineProps<{
  rating: number | null;
  saving: boolean;
  error: string;
}>();

const emit = defineEmits<{
  change: [rating: number | null];
}>();

// Ratings from 0.5 to 5 in increments of 0.5
const ratings = Array.from({ length: 10 }, (_, index) => (index + 1) / 2);

function changeRating(event: Event) {
  const select = event.target as HTMLSelectElement;
  emit("change", select.value === "" ? null : Number(select.value));
}
</script>

<template>
  <div class="book-rating" :aria-busy="saving">
    <label>
      <span>Your rating</span>

      <select :value="rating ?? ''" :disabled="saving" @change="changeRating">
        <option value="">Not rated</option>
        <option v-for="value in ratings" :key="value" :value="value">{{ value }} / 5 stars</option>
      </select>
    </label>

    <span v-if="saving" role="status">Saving…</span>
    <p v-if="error" class="rating-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.book-rating {
  margin-top: var(--spacing-md);
}

label {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
}

select {
  padding: var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg-card);
  color: var(--color-text);
  font: inherit;
}

[role="status"] {
  margin-left: var(--spacing-sm);
  color: var(--color-text-secondary);
}

.rating-error {
  margin-top: var(--spacing-sm);
  color: var(--color-danger);
}
</style>
