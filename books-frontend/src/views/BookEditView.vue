<script setup lang="ts">
import { ref, computed, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getBook, updateBook, deleteBook } from '../api/books'
import type { Book, BookUpdate } from '../api/types'
import NavigationBar from '../components/ui/NavigationBar.vue'
import CoverPickerModal from '../components/modals/CoverPickerModal.vue'
import CoverUpgradeModal from '../components/modals/CoverUpgradeModal.vue'
import { useCachedQuery } from '../composables/useCachedQuery'
import { cacheKeys } from '../cache/keys'
import { cacheDel, cacheInvalidateByPrefix } from '../cache/store'

const route = useRoute()
const router = useRouter()

const bookId = computed(() => {
  const id = parseInt(route.params.id as string)
  return isNaN(id) ? 0 : id
})

const {
  data: book,
  error: bookError,
} = useCachedQuery<Book>(
  computed(() => bookId.value ? cacheKeys.book(bookId.value) : ''),
  () => getBook(bookId.value),
  { enabled: computed(() => bookId.value > 0) }
)

const formData = ref({
  title: '',
  author: '',
  isbn: '',
  description: '',
  published_date: '',
  page_count: '',
  cover_image_url: '',
})

const loading = ref(false)
const error = ref('')
const showCoverPicker = ref(false)
const showCoverUpgrade = ref(false)

const canUpgradeCover = computed(() => {
  const url = book.value?.cover_image_url
  return !!url && !url.startsWith('http')
})

const loadError = computed(() => {
  const e = bookError.value
  if (!e) return ''
  if (e instanceof Error) return e.message
  return 'Failed to load book.'
})

watch(book, (b) => {
  if (b) {
    formData.value = {
      title: b.title,
      author: b.author,
      isbn: b.isbn || '',
      description: b.description || '',
      published_date: (b.published_date ? b.published_date.split('T')[0] : '') || '',
      page_count: b.page_count ? b.page_count.toString() : '',
      cover_image_url: b.cover_image_url || '',
    }
  }
}, { immediate: true })

function handleCoverSelected(imageUrl: string) {
  formData.value.cover_image_url = imageUrl
  showCoverPicker.value = false
}

function handleUpgradeSelected(imageUrl: string) {
  formData.value.cover_image_url = imageUrl
  showCoverUpgrade.value = false
}

async function handleSubmit() {
  if (!book.value) return
  error.value = ''
  loading.value = true

  try {
    const bookData: BookUpdate = {
      title: formData.value.title,
      author: formData.value.author,
      isbn: formData.value.isbn || undefined,
      description: formData.value.description || undefined,
      published_date: formData.value.published_date || undefined,
      page_count: formData.value.page_count ? parseInt(formData.value.page_count) : undefined,
      cover_image_url: formData.value.cover_image_url || undefined,
    }

    await updateBook(book.value.id, bookData)
    await cacheDel(cacheKeys.book(book.value.id))
    await cacheInvalidateByPrefix('lists:')
    router.push({ name: 'book-detail', params: { id: book.value.id } })
  } catch (err: any) {
    console.error('Failed to save book:', err)
    error.value = err.response?.data?.detail || 'Failed to save book. Please try again.'
  } finally {
    loading.value = false
  }
}

function handleCancel() {
  if (loading.value) return
  if (book.value) {
    router.push({ name: 'book-detail', params: { id: book.value.id } })
  } else {
    router.push({ name: 'books' })
  }
}

async function handleDelete() {
  if (!book.value || loading.value) return
  if (!confirm(`Are you sure you want to delete "${book.value.title}"?`)) return

  loading.value = true
  try {
    await deleteBook(book.value.id)
    await cacheInvalidateByPrefix(`books:${book.value.id}`)
    await cacheInvalidateByPrefix('lists:')
    router.push({ name: 'books' })
  } catch (err: any) {
    console.error('Failed to delete book:', err)
    error.value = 'Failed to delete book. Please try again.'
    loading.value = false
  }
}
</script>

<template>
  <div class="book-edit-page">
    <NavigationBar />

    <div class="container">
      <div class="breadcrumb">
        <router-link to="/" class="breadcrumb-link">Books</router-link>
        <span class="breadcrumb-separator">/</span>
        <router-link
          v-if="book"
          :to="{ name: 'book-detail', params: { id: book.id } }"
          class="breadcrumb-link"
        >
          {{ book.title }}
        </router-link>
        <span v-else class="breadcrumb-current">Book</span>
        <span class="breadcrumb-separator">/</span>
        <span class="breadcrumb-current">Edit</span>
      </div>

      <div v-if="loadError && !book" class="error">
        {{ loadError }}
      </div>

      <div v-else-if="!book" class="loading">
        Loading book...
      </div>

      <div v-else class="edit-content">
        <h1>Edit Book</h1>

        <div v-if="error" class="error">
          {{ error }}
        </div>

        <form @submit.prevent="handleSubmit">
          <div class="form-group">
            <label for="title">Title *</label>
            <input
              id="title"
              v-model="formData.title"
              type="text"
              placeholder="Enter book title"
              required
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label for="author">Author *</label>
            <input
              id="author"
              v-model="formData.author"
              type="text"
              placeholder="Enter author name"
              required
              :disabled="loading"
            />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label for="isbn">ISBN</label>
              <input
                id="isbn"
                v-model="formData.isbn"
                type="text"
                placeholder="Enter ISBN"
                :disabled="loading"
              />
            </div>

            <div class="form-group">
              <label for="page_count">Page Count</label>
              <input
                id="page_count"
                v-model="formData.page_count"
                type="number"
                min="0"
                placeholder="Number of pages"
                :disabled="loading"
              />
            </div>
          </div>

          <div class="form-group">
            <label for="published_date">Published Date</label>
            <input
              id="published_date"
              v-model="formData.published_date"
              type="date"
              :disabled="loading"
            />
          </div>

          <div class="form-group">
            <label for="description">Description</label>
            <textarea
              id="description"
              v-model="formData.description"
              rows="4"
              placeholder="Enter book description"
              :disabled="loading"
            ></textarea>
          </div>

          <div class="form-group">
            <label>Cover</label>
            <div class="cover-row">
              <div class="cover-preview" :class="{ empty: !formData.cover_image_url }">
                <img
                  v-if="formData.cover_image_url"
                  :src="formData.cover_image_url"
                  alt="Cover preview"
                />
                <span v-else>No cover</span>
              </div>
              <div class="cover-actions">
                <input
                  v-model="formData.cover_image_url"
                  type="text"
                  placeholder="Cover image URL"
                  :disabled="loading"
                />
                <div class="cover-buttons">
                  <button type="button" @click="showCoverPicker = true" :disabled="loading">
                    Find cover
                  </button>
                  <button
                    type="button"
                    v-if="canUpgradeCover"
                    @click="showCoverUpgrade = true"
                    :disabled="loading"
                  >
                    Upgrade cover
                  </button>
                  <button
                    type="button"
                    v-if="formData.cover_image_url"
                    @click="formData.cover_image_url = ''"
                    :disabled="loading"
                    class="btn-small"
                  >
                    Clear
                  </button>
                </div>
              </div>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="handleDelete" :disabled="loading" class="btn-danger delete-action">
              Delete Book
            </button>
            <button type="button" @click="handleCancel" :disabled="loading">
              Cancel
            </button>
            <button type="submit" class="btn-primary" :disabled="loading">
              {{ loading ? 'Saving...' : 'Save Book' }}
            </button>
          </div>
        </form>
      </div>
    </div>

    <CoverPickerModal
      v-if="showCoverPicker"
      :initial-title="formData.title"
      :initial-author="formData.author"
      :initial-isbn="formData.isbn"
      @select="handleCoverSelected"
      @close="showCoverPicker = false"
    />

    <CoverUpgradeModal
      v-if="showCoverUpgrade && book"
      :book-id="book.id"
      @select="handleUpgradeSelected"
      @close="showCoverUpgrade = false"
    />
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

.cover-row {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
}

.cover-preview {
  width: 90px;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  border-radius: var(--border-radius);
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-actions {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  min-width: 0;
}

.cover-buttons {
  display: flex;
  gap: var(--spacing-sm);
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
