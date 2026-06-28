<script setup lang="ts">
import { computed } from 'vue'
import { type Book } from '../../../api/types'
import { getMediaUrl } from '../../../api/client'
import KebabButton from '../../ui/KebabButton.vue'
import BookCardMeta from './BookCardMeta.vue'
import BookCardStatus from './BookCardStatus.vue'

const props = defineProps<{
  book: Book
}>()

const emit = defineEmits<{
  (e: 'menu', payload: { bookId: number; x: number; y: number }): void
}>()

function openMenu(e: MouseEvent) {
  const rect = (e.currentTarget as HTMLElement).getBoundingClientRect()
  emit('menu', { bookId: props.book.id, x: rect.left, y: rect.bottom + 4 })
}

const detailRoute = computed(() => ({ name: 'book-detail', params: { id: props.book.id } }))
const coverUrl = computed(() => props.book.cover_thumbnail_url || props.book.cover_image_url)
</script>

<template>
  <div class="book-card">
    <KebabButton class="card-menu-button" aria-label="Book actions" @click="openMenu" />
    <div class="book-content">
      <router-link :to="detailRoute" class="book-cover-link">
        <img
          v-if="coverUrl"
          :src="getMediaUrl(coverUrl)"
          :alt="book.title"
          class="book-cover book-cover-clickable"
        />
        <div class="book-cover-placeholder book-cover-clickable" v-else>
          No Cover
        </div>
      </router-link>

      <div class="book-details">
        <div class="book-header">
          <router-link :to="detailRoute" class="book-title-link">
            <h3 class="book-title-clickable">{{ book.title }}</h3>
          </router-link>
        </div>

        <p class="book-author">by {{ book.author }}</p>

        <div v-if="book.description" class="book-description">
          {{ book.description }}
        </div>

        <BookCardMeta :book="book" />

        <BookCardStatus :book="book" />
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-card {
  position: relative;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  padding: var(--spacing-lg);
  margin-bottom: var(--spacing-md);
  transition: box-shadow 0.15s ease;
  overflow: hidden;
}

.card-menu-button {
  position: absolute;
  top: 8px;
  right: 16px;
  z-index: 2;
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
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.book-title-link {
  text-decoration: none;
  color: inherit;
  display: block;
}

.book-cover,
.book-cover-placeholder {
  width: 120px;
  height: auto;
  border-radius: var(--border-radius);
  flex-shrink: 0;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.book-cover {
  display: block;
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
  aspect-ratio: 2 / 3;
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
  padding-right: 44px;
}

.book-header h3 {
  margin: 0;
  font-size: 1.25rem;
  flex: 1;
  word-break: break-word;
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
  word-break: break-word;
}

.book-description {
  margin-bottom: var(--spacing-md);
  line-height: 1.6;
  color: var(--color-text);
  word-break: break-word;
  overflow-wrap: anywhere;
}

@media (max-width: 768px) {
  .book-content {
    flex-direction: column;
  }

  .book-cover,
  .book-cover-placeholder {
    width: 100%;
    height: auto;
  }

  .book-header {
    flex-direction: column;
  }
}
</style>
