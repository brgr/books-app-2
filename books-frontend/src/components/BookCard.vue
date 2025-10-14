<script setup lang="ts">
import { ref } from 'vue'
import { setReadingStatus, removeReadingStatus } from '../api/books'
import { ReadingStatus, type Book } from '../api/types'

const props = defineProps<{
  book: Book
}>()

const emit = defineEmits<{
  updated: []
  deleted: []
}>()

const updatingStatus = ref(false)

const statusOptions = [
  { value: '', label: 'No status' },
  { value: ReadingStatus.WANT_TO_READ, label: 'Want to read' },
  { value: ReadingStatus.STARTED, label: 'Started' },
  { value: ReadingStatus.FINISHED, label: 'Finished' },
  { value: ReadingStatus.ABANDONED, label: 'Abandoned' },
]

function getStatusColor(status: ReadingStatus | null): string {
  if (!status) return 'var(--color-text-secondary)'

  switch (status) {
    case ReadingStatus.WANT_TO_READ:
      return 'var(--color-primary)'
    case ReadingStatus.STARTED:
      return 'var(--color-warning)'
    case ReadingStatus.FINISHED:
      return 'var(--color-success)'
    case ReadingStatus.ABANDONED:
      return 'var(--color-text-secondary)'
    default:
      return 'var(--color-text-secondary)'
  }
}

async function handleStatusChange(event: Event) {
  const newStatus = (event.target as HTMLSelectElement).value
  updatingStatus.value = true

  try {
    if (newStatus === '') {
      // Remove status
      await removeReadingStatus(props.book.id)
    } else {
      // Set status
      await setReadingStatus(props.book.id, {
        status: newStatus as ReadingStatus,
      })
    }
    emit('updated')
  } catch (error) {
    console.error('Failed to update reading status:', error)
    alert('Failed to update reading status')
  } finally {
    updatingStatus.value = false
  }
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString()
}
</script>

<template>
  <div class="book-card">
    <div class="book-header">
      <h3>{{ book.title }}</h3>
      <div class="book-actions">
        <button @click="emit('updated')" class="btn-small" title="Edit book">
          Edit
        </button>
        <button @click="emit('deleted')" class="btn-small btn-danger" title="Delete book">
          Delete
        </button>
      </div>
    </div>

    <p class="book-author">by {{ book.author }}</p>

    <div v-if="book.description" class="book-description">
      {{ book.description }}
    </div>

    <div class="book-meta">
      <span v-if="book.isbn" class="meta-item">
        <strong>ISBN:</strong> {{ book.isbn }}
      </span>
      <span v-if="book.page_count" class="meta-item">
        <strong>Pages:</strong> {{ book.page_count }}
      </span>
      <span v-if="book.published_date" class="meta-item">
        <strong>Published:</strong> {{ formatDate(book.published_date) }}
      </span>
      <span v-if="book.price" class="meta-item">
        <strong>Price:</strong> ${{ book.price.toFixed(2) }}
      </span>
    </div>

    <div class="book-status">
      <label for="status">Reading status:</label>
      <select
        id="status"
        :value="book.user_status?.status || ''"
        @change="handleStatusChange"
        :disabled="updatingStatus"
        :style="{ borderColor: getStatusColor(book.user_status?.status || null) }"
      >
        <option v-for="option in statusOptions" :key="option.value" :value="option.value">
          {{ option.label }}
        </option>
      </select>
    </div>

    <div v-if="book.user_status" class="book-dates text-small text-muted">
      <div v-if="book.user_status.started_at">
        Started: {{ formatDate(book.user_status.started_at) }}
      </div>
      <div v-if="book.user_status.finished_at">
        Finished: {{ formatDate(book.user_status.finished_at) }}
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-card {
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
  transition: box-shadow 0.15s ease;
}

.book-card:hover {
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.15);
}

.book-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: var(--spacing-sm);
}

.book-header h3 {
  margin: 0;
  font-size: 1.25rem;
  flex: 1;
}

.book-actions {
  display: flex;
  gap: var(--spacing-sm);
}

.book-author {
  color: var(--color-text-secondary);
  margin-bottom: var(--spacing-md);
  font-size: 14px;
}

.book-description {
  margin-bottom: var(--spacing-md);
  line-height: 1.6;
  color: var(--color-text);
}

.book-meta {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
  padding-top: var(--spacing-md);
  border-top: 1px solid var(--color-border);
}

.meta-item {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.meta-item strong {
  color: var(--color-text);
}

.book-status {
  margin-bottom: var(--spacing-sm);
}

.book-status label {
  display: inline-block;
  margin-right: var(--spacing-sm);
  margin-bottom: 0;
  font-size: 14px;
}

.book-status select {
  width: auto;
  min-width: 200px;
  display: inline-block;
  border-width: 2px;
  transition: border-color 0.15s ease;
}

.book-dates {
  padding-top: var(--spacing-sm);
  display: flex;
  gap: var(--spacing-md);
}

@media (max-width: 768px) {
  .book-header {
    flex-direction: column;
  }

  .book-actions {
    margin-top: var(--spacing-sm);
  }

  .book-status {
    display: flex;
    flex-direction: column;
  }

  .book-status select {
    width: 100%;
    margin-top: var(--spacing-xs);
  }
}
</style>
