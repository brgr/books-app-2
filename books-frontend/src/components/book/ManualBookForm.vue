<script setup lang="ts">
import { isAxiosError } from "axios";
import { computed, onBeforeUnmount, ref } from "vue";
import { useRouter } from "vue-router";
import { createBook } from "../../api/books";
import { invalidateCache } from "../../cache/invalidate";
import BookFields from "./BookFields.vue";
import { emptyBookForm, formToPayload } from "./bookForm";
import { getPendingCover, isPendingCover } from "./cover/pendingCoverUploads";
import { savePendingCover } from "./cover/savePendingCover";

const router = useRouter();
const formData = ref(emptyBookForm());
const saving = ref(false);
const error = ref("");
const createdBookId = ref<number | null>(null);
const coverUploadFailed = ref(false);
const fieldsDisabled = computed(() => saving.value || createdBookId.value !== null);
let isUnmounted = false;

onBeforeUnmount(() => {
  isUnmounted = true;
});

async function openBook() {
  if (!isUnmounted && createdBookId.value !== null) {
    await router.push({ name: "book-detail", params: { id: createdBookId.value } });
  }
}

async function handleSubmit() {
  if (saving.value) {
    return;
  }
  if (!formData.value.title.trim()) {
    error.value = "Please enter a title.";
    return;
  }

  saving.value = true;
  error.value = "";
  coverUploadFailed.value = false;

  try {
    const cover = formData.value.cover_image_url;
    // Keep the file available if navigating away clears the staged cover while saving.
    const coverFile = getPendingCover(cover);
    if (createdBookId.value === null) {
      const book = await createBook(formToPayload(formData.value));
      createdBookId.value = book.id;
    }
    // The book is already in the library even if its subsequent cover upload fails.
    await invalidateCache.bookAdded();

    if (isPendingCover(cover)) {
      try {
        formData.value.cover_image_url = await savePendingCover(createdBookId.value, cover, coverFile);
      } catch {
        coverUploadFailed.value = true;
        error.value = "Your book was added, but its cover could not be uploaded. Retry or continue without the cover.";
        return;
      }
      await invalidateCache.bookUpdated(createdBookId.value);
    }

    await openBook();
  } catch (err) {
    const detail = isAxiosError<{ detail?: unknown }>(err) ? err.response?.data?.detail : undefined;
    error.value =
      typeof detail === "string" && detail
        ? detail
        : createdBookId.value !== null
          ? "Your book was added, but saving did not finish. Please try again."
          : "Failed to add book. Please try again.";
  } finally {
    saving.value = false;
  }
}

async function continueWithoutCover() {
  if (saving.value) {
    return;
  }
  saving.value = true;
  try {
    await openBook();
  } catch {
    error.value = "Could not open your book. Please try again.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div>
    <p class="text-muted">Enter book details. Only title is required.</p>

    <div v-if="error" class="error" role="alert">{{ error }}</div>

    <form @submit.prevent="handleSubmit">
      <BookFields v-model="formData" :disabled="fieldsDisabled" />

      <div class="form-actions">
        <button
          v-if="coverUploadFailed"
          type="button"
          class="text-link"
          :disabled="saving"
          @click="continueWithoutCover"
        >
          Continue without cover
        </button>
        <button type="submit" class="btn-primary" :disabled="saving || !formData.title.trim()">
          {{ saving ? "Saving..." : createdBookId !== null ? "Retry save" : "Add book" }}
        </button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.form-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: flex-end;
  gap: var(--spacing-md);
  margin-top: var(--spacing-lg);
}
</style>
