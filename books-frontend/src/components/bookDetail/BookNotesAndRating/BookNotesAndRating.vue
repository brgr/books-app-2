<script setup lang="ts">
import { computed, ref, watch } from "vue";
import type { UserBook } from "../../../api/types";
import { useSaveBookNotes } from "../../../composables/bookDetail/useSaveBookNotes";
import { useSaveBookRating } from "../../../composables/bookDetail/useSaveBookRating";
import BookNotes from "./BookNotes.vue";
import BookRating from "./BookRating.vue";

const props = defineProps<{
  userBook: UserBook;
}>();

const { mutateAsync: saveNotes, isPending: savingNotes } = useSaveBookNotes();
const { mutateAsync: saveRating, isPending: savingRating } = useSaveBookRating();
const saving = computed(() => savingNotes.value || savingRating.value);
const error = ref("");

const notes = computed(() => props.userBook.notes ?? "");
const rating = computed(() => props.userBook.rating);

const editing = ref(false);
const draftNotes = ref(notes.value);
const draftRating = ref(rating.value);
const dirty = computed(() => draftNotes.value !== notes.value || draftRating.value !== rating.value);

function reset() {
  draftNotes.value = notes.value;
  draftRating.value = rating.value;
}

// Follow fresh data while reading
watch([notes, rating], () => {
  if (!editing.value) {
    reset();
  }
});

function cancel() {
  reset();
  editing.value = false;
}

async function save() {
  if (!dirty.value || saving.value) {
    return;
  }

  const bookId = props.userBook.book_id;
  error.value = "";

  // Each part shows as saved once its request is done, so after a failure only the other one is still a draft
  try {
    if (draftNotes.value !== notes.value) {
      await saveNotes({ bookId, notes: draftNotes.value });
    }
    if (draftRating.value !== rating.value) {
      await saveRating({ bookId, rating: draftRating.value });
    }
    editing.value = false;
  } catch (err) {
    console.error("Failed to save rating and notes:", err);
    error.value = "Failed to save rating and notes. Please try again.";
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
