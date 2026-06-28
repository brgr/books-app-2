<script setup lang="ts">
import {ref, watch} from 'vue'

const props = defineProps<{
  currentPage?: number | null
  pageCount?: number | null
  progressSaving?: boolean
}>()

const emit = defineEmits<{
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
    <div class="status-row">
      <span class="status-label">Progress</span>
      <span class="status-subtitle">
        <template v-if="currentPage !== null && currentPage !== undefined">
          Page {{ currentPage }}<span v-if="pageCount"> of {{ pageCount }}</span>
        </template>
        <template v-else>No progress yet</template>
      </span>
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
        <span v-if="pageCount" class="progress-total">of {{ pageCount }}</span>
        <button
          class="btn-link"
          type="button"
          data-test="save-progress"
          @click="handleSaveProgress"
          :disabled="progressSaving"
        >
          {{ progressSaving ? 'Saving…' : 'Save' }}
        </button>
        <button
          class="btn-link btn-link-cancel"
          type="button"
          data-test="cancel-progress"
          @click="cancelEditingProgress"
          :disabled="progressSaving"
        >
          Cancel
        </button>
      </span>
      <button
        v-else
        class="btn-link"
        type="button"
        data-test="edit-progress"
        @click="startEditingProgress"
      >
        Update
      </button>
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

.status-row,
.progress-edit {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.9rem;
}

.status-row > .btn-link {
  margin-left: auto;
}

.status-row > .progress-edit {
  flex-basis: 100%;
}

.status-label {
  font-weight: 600;
  color: var(--color-text);
}

.status-subtitle {
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

.progress-total {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
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
