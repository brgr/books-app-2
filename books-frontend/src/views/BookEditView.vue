<script lang="ts" setup>
import { isAxiosError } from "axios";
import { computed, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteBook, getBook, updateBook } from "../api/books";
import type { Book } from "../api/types";
import NavigationBar from "../components/navigation/NavigationBar.vue";
import BookFields from "../components/book/BookFields.vue";
import { bookToForm, emptyBookForm, formToPayload } from "../components/book/bookForm";
import { savePendingCover } from "../components/book/cover/savePendingCover";
import { useCachedQuery } from "../composables/useCachedQuery";
import { cacheKeys } from "../cache/keys";
import { invalidateCache } from "../cache/invalidate";

const route = useRoute();
const router = useRouter();

const bookId = computed(() => {
  const id = parseInt(route.params.id as string);
  return isNaN(id) ? 0 : id;
});

const { data: book, error: bookError } = useCachedQuery<Book>(
  computed(() => (bookId.value ? cacheKeys.book(bookId.value) : "")),
  () => getBook(bookId.value),
  { enabled: computed(() => bookId.value > 0) },
);

const formData = ref(emptyBookForm());

const loading = ref(false);
const error = ref("");

const loadError = computed(() => {
  const e = bookError.value;
  if (!e) {
    return "";
  }
  if (e instanceof Error) {
    return e.message;
  }

  return "Failed to load book.";
});

watch(
  book,
  (b) => {
    if (b) {
      formData.value = bookToForm(b);
    }
  },
  { immediate: true },
);

async function handleSubmit() {
  if (!book.value || loading.value) {
    return;
  }
  if (!formData.value.title.trim() || !formData.value.author.trim()) {
    error.value = "Please enter a title and author.";
    return;
  }

  error.value = "";
  loading.value = true;

  try {
    const bookData = formToPayload(formData.value);
    formData.value.cover_image_url = await savePendingCover(book.value.id, formData.value.cover_image_url);

    await updateBook(book.value.id, bookData);
    await invalidateCache.bookUpdated(book.value.id);

    router.push({ name: "book-detail", params: { id: book.value.id } });
  } catch (err) {
    console.error("Failed to save book:", err);
    const detail = isAxiosError<{ detail?: unknown }>(err) ? err.response?.data?.detail : undefined;
    error.value = typeof detail === "string" && detail ? detail : "Failed to save book. Please try again.";
  } finally {
    loading.value = false;
  }
}

function handleCancel() {
  if (loading.value) {
    return;
  }

  if (book.value) {
    router.push({ name: "book-detail", params: { id: book.value.id } });
  } else {
    router.push({ name: "books" });
  }
}

async function handleDelete() {
  if (!book.value || loading.value) {
    return;
  }
  if (!confirm(`Are you sure you want to delete "${book.value.title}"?`)) {
    return;
  }

  loading.value = true;
  try {
    await deleteBook(book.value.id);
    await invalidateCache.bookDeleted(book.value.id);

    router.push({ name: "books" });
  } catch (err) {
    console.error("Failed to delete book:", err);
    error.value = "Failed to delete book. Please try again.";
    loading.value = false;
  }
}
</script>

<template>
  <div class="book-edit-page">
    <NavigationBar />

    <div class="container">
      <div class="breadcrumb">
        <router-link class="breadcrumb-link" to="/">Books</router-link>
        <span class="breadcrumb-separator">/</span>
        <router-link v-if="book" :to="{ name: 'book-detail', params: { id: book.id } }" class="breadcrumb-link">
          {{ book.title }}
        </router-link>
        <span v-else class="breadcrumb-current">Book</span>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">Edit</span>
      </div>

      <div v-if="loadError && !book" class="error">
        {{ loadError }}
      </div>

      <div v-else-if="!book" class="loading">Loading book...</div>

      <div v-else class="edit-content">
        <h1>Edit Book</h1>

        <div v-if="error" class="error" role="alert">
          {{ error }}
        </div>

        <form @submit.prevent="handleSubmit">
          <BookFields v-model="formData" :book-id="book.id" :disabled="loading" />

          <div class="form-actions">
            <button :disabled="loading" class="btn-danger delete-action" type="button" @click="handleDelete">
              Delete Book
            </button>
            <button :disabled="loading" type="button" @click="handleCancel">Cancel</button>
            <button
              :disabled="loading || !formData.title.trim() || !formData.author.trim()"
              class="btn-primary"
              type="submit"
            >
              {{ loading ? "Saving..." : "Save Book" }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-edit-page {
  min-height: 100vh;
  background-color: var(--color-bg);
}

.breadcrumb {
  display: flex;
  align-items: center;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
  flex-wrap: wrap;
}

.breadcrumb-link {
  color: var(--color-text);
  text-decoration: none;
  font-weight: 600;
}

.breadcrumb-link:hover {
  color: var(--color-primary);
}

.breadcrumb-separator {
  color: var(--color-text-secondary);
}

.breadcrumb-current {
  color: var(--color-text-secondary);
  max-width: min(420px, 60vw);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.edit-content {
  max-width: 720px;
}

.edit-content h1 {
  margin: 0 0 var(--spacing-lg) 0;
  font-size: 1.75rem;
}

.form-actions {
  display: flex;
  gap: var(--spacing-md);
  justify-content: flex-end;
  margin-top: var(--spacing-xl);
}

.form-actions .delete-action {
  margin-right: auto;
}
</style>
