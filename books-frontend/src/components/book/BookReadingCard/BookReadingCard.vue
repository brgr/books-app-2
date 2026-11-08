<script setup lang="ts">
import { computed, ref, watch } from "vue";
import BookShelfButton from "../BookShelfButton/BookShelfButton.vue";
import BookProgressEditor from "./BookProgressEditor.vue";
import type { ReadingProgress } from "./types";
import { type BookProgressUpdate, type ReadingDateValue, ReadingShelf } from "../../../api/types";
import { formatReadingDate } from "../../../utils/date";

const props = defineProps<{
  shelf: ReadingShelf | null;
  updating?: boolean;
  currentPage?: number | null;
  currentPercent?: number | null;
  pageCount?: number | null;
  startedAt?: ReadingDateValue | null;
  finishedAt?: ReadingDateValue | null;
  progressSaving?: boolean;
}>();

const emit = defineEmits<{
  change: [shelf: ReadingShelf, readingDate?: ReadingDateValue];
  "update-progress": [progress: BookProgressUpdate];
}>();

const hasPage = computed(() => props.currentPage !== null && props.currentPage !== undefined);
const hasPercent = computed(() => props.currentPercent !== null && props.currentPercent !== undefined);

// A percentage to show alongside the page: taken directly when the user tracks
// by percent, otherwise derived from the page and the book's length. Null when
// we can't express one (page tracked but unknown length).
const displayPercent = computed<number | null>(() => {
  if (hasPercent.value) {
    return Math.min(100, Math.max(0, Math.round(props.currentPercent as number)));
  }
  if (hasPage.value && props.pageCount) {
    return Math.min(100, Math.round(((props.currentPage as number) / props.pageCount) * 100));
  }
  return null;
});

// Keep both recorded values available when switching the editor's unit.
const editorProgress = computed<ReadingProgress | null>(() => {
  if (props.currentPage !== null && props.currentPage !== undefined) {
    return { page: props.currentPage, percent: props.currentPercent ?? undefined };
  }
  if (props.currentPercent !== null && props.currentPercent !== undefined) {
    return { percent: props.currentPercent };
  }
  return null;
});

const editingProgress = ref(false);

watch(
  () => [props.currentPage, props.currentPercent],
  () => {
    editingProgress.value = false;
  },
);
</script>

<template>
  <div class="reading-card" data-test="reading-card">
    <div class="reading-header">
      <div class="reading-status">
        <span class="reading-label">Currently Reading</span>
        <span v-if="startedAt" class="since">since {{ formatReadingDate(startedAt) }}</span>
      </div>
      <div class="progress-summary">
        <span v-if="displayPercent !== null" class="progress-percent">{{ displayPercent }}%</span>
        <span v-if="hasPage" class="muted progress-detail">
          Page {{ currentPage }}<span v-if="pageCount"> of {{ pageCount }}</span>
        </span>
        <span v-else-if="!hasPercent" class="muted progress-detail">No progress yet</span>
      </div>
    </div>

    <div
      v-if="displayPercent !== null"
      class="progress-track"
      role="progressbar"
      aria-label="Reading progress"
      :aria-valuenow="displayPercent"
      :aria-valuemin="0"
      :aria-valuemax="100"
    >
      <div class="progress-fill" :style="{ width: `${displayPercent}%` }"></div>
    </div>

    <BookProgressEditor
      v-if="editingProgress"
      :progress="editorProgress"
      :page-count="pageCount"
      :is-currently-saving="progressSaving"
      @save="(progress) => emit('update-progress', progress)"
      @cancel="editingProgress = false"
    />

    <div v-if="finishedAt" class="dates">
      <span>· Finished {{ formatReadingDate(finishedAt) }}</span>
    </div>

    <div class="reading-actions">
      <button
        v-if="!editingProgress"
        class="update-progress"
        type="button"
        data-test="edit-progress"
        @click="editingProgress = true"
      >
        Update progress
      </button>
      <BookShelfButton
        :shelf="shelf"
        :updating="updating ?? false"
        @change="(shelf, readingDate) => emit('change', shelf, readingDate)"
      />
    </div>
  </div>
</template>

<style scoped>
.reading-card {
  background: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  padding: var(--spacing-md);
  display: inline-flex;
  flex-direction: column;
  gap: var(--spacing-md);
  width: 360px;
  max-width: 100%;
  text-align: left;
}

.reading-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
}

.reading-status,
.progress-summary {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.progress-summary {
  align-items: flex-end;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.progress-percent {
  font-size: 1.75rem;
  font-weight: 600;
  line-height: 1.1;
}

.progress-detail {
  font-size: 0.8rem;
}

.progress-track {
  height: 6px;
  background: var(--color-border);
  border-radius: 999px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--color-primary);
  border-radius: inherit;
}

.reading-label {
  font-weight: 600;
}

.since {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
}

.reading-actions {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.update-progress {
  background: var(--color-primary);
  border-color: var(--color-primary);
  color: var(--color-bg);
  padding: var(--spacing-sm) 12px;
}

.update-progress:hover {
  background: var(--color-primary-hover);
  border-color: var(--color-primary-hover);
}

.reading-actions :deep(.shelf-control) {
  margin-inline: auto 0;
  align-self: auto;
}

.reading-actions :deep(.shelf-button),
.reading-actions :deep(.shelf-caret) {
  background: transparent;
  border-color: var(--color-border);
  color: var(--color-text);
  min-height: 40px;
}

.reading-actions :deep(.shelf-button) {
  border-radius: var(--border-radius) 0 0 var(--border-radius);
}

.reading-actions :deep(.shelf-caret) {
  border-left: 0;
  border-radius: 0 var(--border-radius) var(--border-radius) 0;
}

.reading-actions :deep(.shelf-menu) {
  left: auto;
  right: 0;
}

.dates {
  display: flex;
  gap: var(--spacing-xs);
  font-size: 0.8rem;
  color: var(--color-text-secondary);
}

.muted {
  color: var(--color-text-secondary);
}
</style>
