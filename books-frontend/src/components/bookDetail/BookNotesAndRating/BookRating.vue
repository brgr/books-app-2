<script setup lang="ts">
import { computed, ref, useId } from "vue";

const props = defineProps<{
  editing: boolean;
  disabled?: boolean;
}>();

const rating = defineModel<number | null>({ required: true });

const emit = defineEmits<{
  edit: [];
}>();

// Ratings from 0.5 to 5 in increments of 0.5
const ratings = Array.from({ length: 10 }, (_, index) => (index + 1) / 2);
const name = useId();
const preview = ref<number | null>(null);
const displayed = computed(() => preview.value ?? rating.value ?? 0);
const starPath = "m12 3 2.78 5.63L21 9.54l-4.5 4.39 1.06 6.2L12 17.2l-5.56 2.93 1.06-6.2L3 9.54l6.22-.91Z";

function startEditing(event: Event) {
  if (!props.editing) {
    event.preventDefault();
    emit("edit");
  }
}
</script>

<template>
  <div class="book-rating">
    <div
      class="stars"
      :role="editing ? 'radiogroup' : 'button'"
      :tabindex="editing ? undefined : 0"
      :aria-label="
        editing ? 'Your rating' : `Edit rating: ${rating === null ? 'Not rated' : `${rating} out of 5 stars`}`
      "
      @click="startEditing"
      @keydown.enter="startEditing"
      @keydown.space="startEditing"
      @pointerleave="preview = null"
    >
      <svg v-for="star in 5" :key="star" viewBox="0 0 24 24" aria-hidden="true">
        <path :d="starPath" class="star-track" />
        <path
          :d="starPath"
          class="star-fill"
          :style="{ clipPath: `inset(0 ${100 - Math.min(1, Math.max(0, displayed - star + 1)) * 100}% 0 0)` }"
        />
      </svg>
      <input
        v-for="value in editing ? ratings : []"
        :key="value"
        v-model="rating"
        type="radio"
        :name="name"
        :value="value"
        :aria-label="`${value} out of 5 stars`"
        :disabled="disabled"
        :style="{ left: `${(value - 0.5) * 20}%` }"
        @pointerenter="!disabled && $event.pointerType === 'mouse' && (preview = value)"
        @change="preview = null"
      />
    </div>
    <button
      v-if="editing && rating !== null"
      type="button"
      class="text-link clear-rating"
      :disabled="disabled"
      @click="rating = null"
    >
      Clear
    </button>
    <span v-if="rating === null" class="not-rated">Not rated</span>
  </div>
</template>

<style scoped>
.book-rating {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.stars {
  position: relative;
  display: flex;
  align-items: center;
  width: 130px;
  height: 40px;
  cursor: pointer;
  touch-action: manipulation;
  -webkit-tap-highlight-color: transparent;
}

.stars:focus-visible,
.stars:has(input:focus-visible) {
  outline: 2px solid var(--color-primary);
  border-radius: var(--border-radius);
}

svg {
  width: 20%;
  height: 26px;
}

path {
  stroke-width: 2;
  stroke-linejoin: round;
}

.star-track {
  fill: var(--color-text-secondary);
  stroke: var(--color-text-secondary);
  opacity: 0.3;
}

.star-fill {
  fill: var(--color-warning);
  stroke: var(--color-warning);
}

input {
  position: absolute;
  width: 10%;
  height: 100%;
  margin: 0;
  opacity: 0;
  cursor: pointer;
}

.clear-rating,
.not-rated {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

@media (pointer: coarse) {
  .stars {
    width: 170px;
    height: 44px;
  }
}
</style>
