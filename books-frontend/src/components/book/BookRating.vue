<script setup lang="ts">
import { ref, useId, watch } from "vue";

const props = defineProps<{
  rating: number | null;
  saving: boolean;
  error: string;
}>();

const emit = defineEmits<{
  change: [rating: number | null];
}>();

// Ratings from 0.5 to 5 in increments of 0.5
const ratings = Array.from({ length: 10 }, (_, index) => (index + 1) / 2);
const name = useId();
const selected = ref(props.rating);
// After a failed save, the user can try again with the same rating, and it will be sent again.
watch([() => props.rating, () => props.saving], () => {
  if (!props.saving) {
    selected.value = props.rating;
  }
});
const starPath = "m12 3 2.78 5.63L21 9.54l-4.5 4.39 1.06 6.2L12 17.2l-5.56 2.93 1.06-6.2L3 9.54l6.22-.91Z";

function changeRating(rating: number | null) {
  selected.value = rating;
  emit("change", rating);
}
</script>

<template>
  <div class="book-rating" :aria-busy="saving">
    <div class="stars" role="radiogroup" aria-label="Your rating">
      <svg v-for="star in 5" :key="star" viewBox="0 0 24 24" aria-hidden="true">
        <path :d="starPath" class="star-outline" />
        <path
          :d="starPath"
          class="star-fill"
          :style="{ clipPath: `inset(0 ${100 - Math.min(1, Math.max(0, (rating ?? 0) - star + 1)) * 100}% 0 0)` }"
        />
      </svg>
      <input
        v-for="value in ratings"
        :key="value"
        v-model="selected"
        type="radio"
        :name="name"
        :value="value"
        :aria-label="`${value} out of 5 stars`"
        :disabled="saving"
        :style="{ left: `${(value - 0.5) * 20}%` }"
        @change="changeRating(value)"
      />
    </div>
    <button
      v-if="rating !== null"
      type="button"
      class="text-link clear-rating"
      :disabled="saving"
      @click="changeRating(null)"
    >
      Clear rating
    </button>

    <span v-if="saving" role="status">Saving…</span>
    <p v-if="error" class="rating-error" role="alert">{{ error }}</p>
  </div>
</template>

<style scoped>
.book-rating {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--spacing-sm);
}

.stars {
  position: relative;
  display: flex;
  width: 160px;
  height: 44px;
}

.stars:has(input:focus-visible) {
  outline: 2px solid var(--color-primary);
  border-radius: var(--border-radius);
}

svg {
  width: 20%;
  height: 100%;
}

.star-outline {
  fill: none;
  stroke: var(--color-text-secondary);
}

.star-fill {
  fill: var(--color-warning);
}

input {
  position: absolute;
  width: 10%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

[role="status"] {
  color: var(--color-text-secondary);
}

.rating-error {
  flex-basis: 100%;
  margin-top: var(--spacing-sm);
  color: var(--color-danger);
}
</style>
