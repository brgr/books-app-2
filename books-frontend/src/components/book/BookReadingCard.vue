<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import BookStatusPill from './BookStatusPill.vue'
import BookProgressBar from './BookProgressBar.vue'
import {ReadingStatus} from '../../api/types'
import {formatShortDate} from '../../utils/date'

const props = defineProps<{
  status: ReadingStatus | null
  updating?: boolean
  currentPage?: number | null
  pageCount?: number | null
  startedAt?: string | null
  finishedAt?: string | null
  progressSaving?: boolean
}>()

const emit = defineEmits<{
  change: [status: ReadingStatus]
  'update-progress': [page: number]
}>()

const progressDraft = ref<string>(props.currentPage?.toString() ?? '')
const editingProgress = ref(false)

watch(
  () => props.currentPage,
  (val) => {
    progressDraft.value = val?.toString() ?? ''
    editingProgress.value = false
  },
)

const hasProgress = computed(
  () => props.currentPage !== null && props.currentPage !== undefined,
)

function handleSaveProgress() {
  if (props.progressSaving) return
  const trimmed = String(progressDraft.value ?? '').trim()
  if (!trimmed) {
    alert('Please enter a page number.')
    return
  }
  const page = Number.parseInt(trimmed, 10)
  if (Number.isNaN(page) || page < 0) {
    alert('Please enter a valid page number.')
    return
  }
  emit('update-progress', page)
}

function handleProgressFocus(event: FocusEvent) {
  const target = event.target as HTMLInputElement | null
  target?.select()
}

function startEditingProgress() {
  progressDraft.value = props.currentPage?.toString() ?? ''
  editingProgress.value = true
}

function cancelEditingProgress() {
  progressDraft.value = props.currentPage?.toString() ?? ''
  editingProgress.value = false
}
</script>

<template>
  <div class="status-card" data-test="status-card">
    <BookStatusPill :status="status" :updating="updating ?? false" @change="emit('change', $event)" />

    <BookProgressBar :current-page="currentPage" :page-count="pageCount" />

    <div class="progress-line">
      <span v-if="editingProgress" class="progress-edit">
        <input
          v-model="progressDraft"
          type="number"
          min="0"
          inputmode="numeric"
          pattern="[0-9]*"
          class="progress-input"
          data-test="progress-input"
          :disabled="progressSaving"
          placeholder="Page"
          @focus="handleProgressFocus"
        />
        <span v-if="pageCount" class="muted">of {{ pageCount }}</span>
        <button
          class="btn-link"
          type="button"
          data-test="save-progress"
          :disabled="progressSaving"
          @click="handleSaveProgress"
        >
          {{ progressSaving ? 'Saving…' : 'Save' }}
        </button>
        <button
          class="btn-link btn-link-cancel"
          type="button"
          data-test="cancel-progress"
          :disabled="progressSaving"
          @click="cancelEditingProgress"
        >
          Cancel
        </button>
      </span>
      <template v-else>
        <span class="muted">
          <template v-if="hasProgress">Page {{ currentPage }}<span v-if="pageCount"> of {{ pageCount }}</span></template>
          <template v-else>No progress yet</template>
        </span>
        <button
          class="btn-link"
          type="button"
          data-test="edit-progress"
          @click="startEditingProgress"
        >
          Update
        </button>
      </template>
    </div>

    <div v-if="startedAt || finishedAt" class="dates">
      <span v-if="startedAt">Started {{ formatShortDate(startedAt) }}</span>
      <span v-if="finishedAt">· Finished {{ formatShortDate(finishedAt) }}</span>
    </div>
  </div>
</template>

<style scoped>
.status-card {
  background: rgba(12, 8, 16, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.12);
  border-radius: var(--border-radius);
  padding: var(--spacing-lg);
  box-shadow: 0 10px 20px rgba(7, 5, 8, 0.2);
  display: inline-flex;
  flex-direction: column;
  gap: var(--spacing-md);
  width: fit-content;
  max-width: 100%;
}

.progress-line,
.progress-edit {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  flex-wrap: wrap;
  font-size: 0.9rem;
}

.progress-line > .btn-link {
  margin-left: auto;
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

.progress-input {
  width: 70px;
  padding: 4px var(--spacing-sm);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.9rem;
  appearance: textfield;
  -moz-appearance: textfield;
}

.progress-input::-webkit-outer-spin-button,
.progress-input::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.btn-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--color-primary);
  font-size: 0.9rem;
  cursor: pointer;
}

.btn-link:hover:not(:disabled) {
  text-decoration: underline;
}

.btn-link:disabled {
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

.btn-link-cancel {
  color: var(--color-danger);
}
</style>
