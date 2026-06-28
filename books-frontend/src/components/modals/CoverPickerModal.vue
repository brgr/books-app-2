<script setup lang="ts">
import { ref, watch } from 'vue'
import { searchBookCovers } from '../../api/books'
import type { CoverSearchResult } from '../../api/types'

const props = defineProps<{
  initialTitle?: string
  initialAuthor?: string
  initialIsbn?: string
}>()

const emit = defineEmits<{
  close: []
  select: [imageUrl: string]
}>()

const title = ref(props.initialTitle ?? '')
const author = ref(props.initialAuthor ?? '')
const isbn = ref(props.initialIsbn ?? '')
const results = ref<CoverSearchResult[]>([])
const loading = ref(false)
const error = ref('')
const hasSearched = ref(false)

async function handleSearch() {
  if (!title.value.trim() && !author.value.trim() && !isbn.value.trim()) {
    error.value = 'Enter a title, author, or ISBN'
    return
  }
  error.value = ''
  loading.value = true
  hasSearched.value = true
  try {
    results.value = await searchBookCovers({
      title: title.value.trim() || undefined,
      author: author.value.trim() || undefined,
      isbn: isbn.value.trim() || undefined,
    })
  } catch (err: any) {
    console.error('Cover search failed:', err)
    error.value = err.response?.data?.detail || 'Failed to search covers.'
  } finally {
    loading.value = false
  }
}

function handleSelect(result: CoverSearchResult) {
  emit('select', result.image_url)
}

function handleClose() {
  emit('close')
}

watch(
  () => [props.initialTitle, props.initialAuthor, props.initialIsbn],
  () => {
    if (!hasSearched.value && (props.initialTitle || props.initialAuthor || props.initialIsbn)) {
      handleSearch()
    }
  },
  { immediate: true },
)
</script>

<template>
  <div class="modal-overlay" @click.self="handleClose">
    <div class="modal">
      <div class="modal-header">
        <h3>Find a Cover</h3>
        <button @click="handleClose" class="btn-small">Close</button>
      </div>

      <div class="modal-body">
        <div class="search-fields">
          <input v-model="title" type="text" placeholder="Title" :disabled="loading" @keyup.enter="handleSearch" />
          <input v-model="author" type="text" placeholder="Author" :disabled="loading" @keyup.enter="handleSearch" />
          <input v-model="isbn" type="text" placeholder="ISBN (overrides title/author)" :disabled="loading" @keyup.enter="handleSearch" />
          <button @click="handleSearch" class="btn-primary" :disabled="loading">
            {{ loading ? 'Searching...' : 'Search' }}
          </button>
        </div>

        <div v-if="error" class="error">{{ error }}</div>

        <div v-if="loading" class="loading">Loading covers...</div>

        <div v-else-if="hasSearched && results.length === 0" class="empty-state">
          <p>No covers found. Try a different combination.</p>
        </div>

        <div v-else-if="results.length > 0" class="cover-grid">
          <button
            v-for="(result, index) in results"
            :key="result.google_books_id || index"
            class="cover-tile"
            @click="handleSelect(result)"
            :title="`${result.title}${result.author ? ' — ' + result.author : ''}`"
          >
            <img :src="result.thumbnail" :alt="result.title" loading="lazy" />
            <div class="cover-caption">
              <span class="cover-title">{{ result.title }}</span>
              <span v-if="result.author" class="cover-author">{{ result.author }}</span>
            </div>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.search-fields {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: var(--spacing-sm);
  margin-bottom: var(--spacing-md);
}

.search-fields input:nth-child(3),
.search-fields button {
  grid-column: span 2;
}

.cover-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: var(--spacing-md);
  max-height: 60vh;
  overflow-y: auto;
}

.cover-tile {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.15s ease, transform 0.15s ease;
}

.cover-tile:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
}

.cover-tile img {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--color-bg);
}

.cover-caption {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
  min-height: 2.4em;
}

.cover-title {
  color: var(--color-text);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.cover-author {
  color: var(--color-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

@media (max-width: 768px) {
  .search-fields {
    grid-template-columns: 1fr;
  }
  .search-fields input:nth-child(3),
  .search-fields button {
    grid-column: span 1;
  }
}
</style>
