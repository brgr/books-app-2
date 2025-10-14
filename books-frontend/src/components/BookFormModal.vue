<script setup lang="ts">
import { ref, watch } from 'vue'
import { createBook, updateBook } from '../api/books'
import type { Book, BookCreate, BookUpdate, GoogleBookResult } from '../api/types'

const props = defineProps<{
  book?: Book | null
  prefilledData?: GoogleBookResult | null
}>()

const emit = defineEmits<{
  close: []
  saved: []
}>()

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

// Initialize form with book data if editing or with prefilled data from search
watch(() => props.book, (book) => {
  if (book) {
    formData.value = {
      title: book.title,
      author: book.author,
      isbn: book.isbn || '',
      description: book.description || '',
      published_date: (book.published_date ? book.published_date.split('T')[0] : '') || '',
      page_count: book.page_count ? book.page_count.toString() : '',
      cover_image_url: book.cover_image_url || '',
    }
  } else {
    resetForm()
  }
}, { immediate: true })

// Watch for prefilled data from Google Books search
watch(() => props.prefilledData, (data) => {
  if (data && !props.book) {
    formData.value = {
      title: data.title || '',
      author: data.author || '',
      isbn: data.isbn || '',
      description: data.description || '',
      published_date: (data.published_date ? data.published_date.split('T')[0] : '') || '',
      page_count: data.page_count ? data.page_count.toString() : '',
      cover_image_url: data.thumbnail || '',
    }
  }
}, { immediate: true })

function resetForm() {
  formData.value = {
    title: '',
    author: '',
    isbn: '',
    description: '',
    published_date: '',
    page_count: '',
    cover_image_url: '',
  }
  error.value = ''
}

async function handleSubmit() {
  error.value = ''
  loading.value = true

  try {
    const bookData: BookCreate | BookUpdate = {
      title: formData.value.title,
      author: formData.value.author,
      isbn: formData.value.isbn || undefined,
      description: formData.value.description || undefined,
      published_date: formData.value.published_date || undefined,
      page_count: formData.value.page_count ? parseInt(formData.value.page_count) : undefined,
      cover_image_url: formData.value.cover_image_url || undefined,
    }

    if (props.book) {
      // Update existing book
      await updateBook(props.book.id, bookData as BookUpdate)
    } else {
      // Create new book
      await createBook(bookData as BookCreate)
    }

    emit('saved')
    emit('close')
  } catch (err: any) {
    console.error('Failed to save book:', err)
    error.value = err.response?.data?.detail || 'Failed to save book. Please try again.'
  } finally {
    loading.value = false
  }
}

function handleClose() {
  if (!loading.value) {
    emit('close')
  }
}
</script>

<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal">
      <div class="modal-header">
        <h3>{{ book ? 'Edit Book' : 'Add New Book' }}</h3>
        <button @click="handleClose" :disabled="loading" class="btn-small">
          Close
        </button>
      </div>

      <div class="modal-body">
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
        </form>
      </div>

      <div class="modal-footer">
        <button @click="handleClose" :disabled="loading">
          Cancel
        </button>
        <button @click="handleSubmit" class="btn-primary" :disabled="loading">
          {{ loading ? 'Saving...' : 'Save Book' }}
        </button>
      </div>
    </div>
  </div>
</template>
