<script setup lang="ts">
import { computed, ref, watch } from "vue";
import BookNotes from "./BookNotes.vue";
import BookRating from "./BookRating.vue";

const props = defineProps<{
  notes: string;
  rating: number | null;
  saving: boolean;
  error: string;
}>();

const emit = defineEmits<{
  save: [notes: string, rating: number | null];
}>();

const editing = ref(false);
const draftNotes = ref(props.notes);
const draftRating = ref(props.rating);
const dirty = computed(() => draftNotes.value !== props.notes || draftRating.value !== props.rating);

function reset() {
  draftNotes.value = props.notes;
  draftRating.value = props.rating;
}

// Follow fresh data while reading, and close the form once everything it changed is saved.
watch([() => props.notes, () => props.rating, () => props.saving], () => {
  if (!editing.value) {
    reset();
  } else if (!props.saving && !dirty.value) {
    editing.value = false;
  }
});

function cancel() {
  reset();
  editing.value = false;
}

function save() {
  if (dirty.value && !props.saving) {
    emit("save", draftNotes.value, draftRating.value);
  }
}
</script>

<template>
  <section class="book-notes-and-rating">
    <h2>Rating &amp; notes</h2>
    <div class="review-card" :class="{ editing }">
      <BookRating v-model="draftRating" :editing="editing" :disabled="saving" @edit="editing = true" />
      <BookNotes v-model="draftNotes" :editing="editing" :disabled="saving" @submit="save" />
    </div>
    <p v-if="error" class="review-error" role="alert">{{ error }}</p>
    <div class="review-actions">
      <template v-if="editing">
        <button type="button" class="btn-secondary" data-test="cancel" :disabled="saving" @click="cancel">
          Cancel
        </button>
        <button type="button" class="btn-primary" data-test="save" :disabled="saving || !dirty" @click="save">
          {{ saving ? "Saving..." : "Save" }}
        </button>
      </template>
      <button v-else type="button" class="btn-secondary" data-test="edit" @click="editing = true">Edit</button>
    </div>
  </section>
</template>

<style scoped>
.book-notes-and-rating {
  margin-bottom: var(--spacing-xl);
}

h2 {
  font-size: 1.25rem;
}

.review-card {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  padding: var(--spacing-xs) var(--spacing-md) var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg);
}

.review-card.editing {
  border-color: var(--color-primary);
}

.review-error {
  margin: var(--spacing-sm) 0 0;
  color: var(--color-danger);
}

.review-actions {
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
  margin-top: var(--spacing-sm);
}
</style>
