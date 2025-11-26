<script setup lang="ts">
import { computed } from 'vue'
import { ReadingStatus, type Book } from '../api/types'

const props = defineProps<{
  book: Book
}>()

const readingStatus = computed(() => props.book.user_status?.status || null)

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

function getStatusLabel(status: ReadingStatus | null): string {
  if (!status) return 'N/A'

  const labels: Record<ReadingStatus, string> = {
    [ReadingStatus.WANT_TO_READ]: 'Want to read',
    [ReadingStatus.STARTED]: 'Started',
    [ReadingStatus.FINISHED]: 'Finished',
    [ReadingStatus.ABANDONED]: 'Abandoned',
  }

  return labels[status] || status
}

function formatDate(dateStr: string | null): string {
  if (!dateStr) return 'N/A'
  return new Date(dateStr).toLocaleDateString()
}
</script>

<template>
  <div class="book-card">
    <div class="book-content">
      <router-link :to="{ name: 'book-detail', params: { id: book.id } }" class="book-cover-link">
        <img
          v-if="book.cover_image_url"
          :src="book.cover_image_url"
          :alt="book.title"
          class="book-cover book-cover-clickable"
        />
        <div class="book-cover-placeholder book-cover-clickable" v-else>
          No Cover
        </div>
      </router-link>

      <div class="book-details">
        <div class="book-header">
          <router-link :to="{ name: 'book-detail', params: { id: book.id } }" class="book-title-link">
            <h3 class="book-title-clickable">{{ book.title }}</h3>
          </router-link>
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
    </div>

    <div v-if="readingStatus" class="book-status">
      <span class="book-status-label">Reading status:</span>
      <span
        class="book-status-pill"
        :style="{ borderColor: getStatusColor(readingStatus), color: getStatusColor(readingStatus) }"
      >
        {{ getStatusLabel(readingStatus) }}
      </span>
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
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
}

.book-content {
  display: flex;
  gap: var(--spacing-lg);
}

.book-cover-link {
  text-decoration: none;
  display: block;
}

.book-title-link {
  text-decoration: none;
  color: inherit;
  display: block;
}

.book-cover,
.book-cover-placeholder {
  width: 120px;
  height: 180px;
  object-fit: cover;
  border-radius: var(--border-radius);
  flex-shrink: 0;
}

.book-cover-clickable {
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}

.book-cover-clickable:hover {
  transform: scale(1.02);
  box-shadow: 0 4px 8px rgba(0, 0, 0, 0.2);
}

.book-cover-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 12px;
  text-align: center;
}

.book-details {
  flex: 1;
  min-width: 0;
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

.book-title-clickable {
  cursor: pointer;
  transition: color 0.15s ease;
}

.book-title-clickable:hover {
  color: var(--color-primary);
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
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
}

.book-status-label {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.book-status-pill {
  border: 1px solid var(--color-border);
  border-radius: 999px;
  padding: 4px 12px;
  font-size: 13px;
  font-weight: 600;
}

.book-dates {
  padding-top: var(--spacing-sm);
  display: flex;
  gap: var(--spacing-md);
}

@media (max-width: 768px) {
  .book-content {
    flex-direction: column;
  }

  .book-cover,
  .book-cover-placeholder {
    width: 100%;
    height: 240px;
  }

  .book-header {
    flex-direction: column;
  }

  .book-status {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
