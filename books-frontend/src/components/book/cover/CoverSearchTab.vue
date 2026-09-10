<script setup lang="ts">
import { ref, watch } from "vue";
import { isAxiosError } from "axios";
import { searchBookCovers } from "../../../api/covers";
import type { CoverSearchResult } from "../../../api/types";
import CoverCandidateGrid from "./CoverCandidateGrid.vue";
import CoverCandidateTile from "./CoverCandidateTile.vue";

const props = defineProps<{
  initialTitle?: string;
  initialAuthor?: string;
  initialIsbn?: string;
}>();

const emit = defineEmits<{
  select: [imageUrl: string];
}>();

const title = ref(props.initialTitle ?? "");
const author = ref(props.initialAuthor ?? "");
const isbn = ref(props.initialIsbn ?? "");
const results = ref<CoverSearchResult[]>([]);
const loading = ref(false);
const error = ref("");
const hasSearched = ref(false);

async function handleSearch() {
  if (!title.value.trim() && !author.value.trim() && !isbn.value.trim()) {
    error.value = "Enter a title, author, or ISBN";
    return;
  }
  error.value = "";
  loading.value = true;
  hasSearched.value = true;
  try {
    results.value = await searchBookCovers({
      title: title.value.trim() || undefined,
      author: author.value.trim() || undefined,
      isbn: isbn.value.trim() || undefined,
    });
  } catch (err: unknown) {
    console.error("Cover search failed:", err);
    const detail = isAxiosError<{ detail?: unknown }>(err) ? err.response?.data?.detail : undefined;
    error.value = typeof detail === "string" && detail ? detail : "Failed to search covers.";
  } finally {
    loading.value = false;
  }
}

watch(
  () => [props.initialTitle, props.initialAuthor, props.initialIsbn],
  () => {
    if (!hasSearched.value && (props.initialTitle || props.initialAuthor || props.initialIsbn)) {
      handleSearch();
    }
  },
  { immediate: true },
);
</script>

<template>
  <div class="search-fields">
    <input v-model="title" type="text" placeholder="Title" :disabled="loading" @keyup.enter="handleSearch" />
    <input v-model="author" type="text" placeholder="Author" :disabled="loading" @keyup.enter="handleSearch" />
    <input
      v-model="isbn"
      type="text"
      placeholder="ISBN (overrides title/author)"
      :disabled="loading"
      @keyup.enter="handleSearch"
    />
    <button @click="handleSearch" class="btn-primary" :disabled="loading">
      {{ loading ? "Searching..." : "Search" }}
    </button>
  </div>

  <div v-if="error" class="error">{{ error }}</div>

  <div v-if="loading" class="loading">Loading covers...</div>

  <div v-else-if="hasSearched && results.length === 0" class="empty-state">
    <p>No covers found. Try a different combination.</p>
  </div>

  <CoverCandidateGrid v-else-if="results.length > 0">
    <CoverCandidateTile
      v-for="(result, index) in results"
      :key="result.google_books_id || index"
      :thumbnail-url="result.thumbnail"
      :alt="result.title"
      @select="emit('select', result.image_url)"
      :title="`${result.title}${result.author ? ' — ' + result.author : ''}`"
    >
      <span class="cover-title">{{ result.title }}</span>
      <span v-if="result.author" class="cover-author">{{ result.author }}</span>
    </CoverCandidateTile>
  </CoverCandidateGrid>
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

.cover-tile :deep(.cover-caption) {
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
