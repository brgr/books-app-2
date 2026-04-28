<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {ReadingStatus} from '../api/types'

const props = defineProps<{
  status: ReadingStatus | null
  statusLabel: string
  statusSubtitle: string
  updating: boolean
  currentPage?: number | null
  pageCount?: number | null
  progressSaving?: boolean
}>()

const emit = defineEmits<{
  start: [payload: {occurredAt?: string}]
  finish: [payload: {occurredAt?: string}]
  'update-progress': [page: number]
}>()

function todayIsoDate(): string {
  const now = new Date()
  const y = now.getFullYear()
  const m = String(now.getMonth() + 1).padStart(2, '0')
  const d = String(now.getDate()).padStart(2, '0')
  return `${y}-${m}-${d}`
}

const dateDraft = ref(todayIsoDate())

watch(
  () => [props.status],
  () => { dateDraft.value = todayIsoDate() },
)

function resolveOccurredAt(): string | undefined {
  const picked = dateDraft.value
  if (!picked || picked === todayIsoDate()) return undefined
  return new Date(`${picked}T12:00:00`).toISOString()
}

const canStart = computed(
  () => props.status === null || props.status === ReadingStatus.WANT_TO_READ,
)
const canFinish = computed(() => props.status === ReadingStatus.STARTED)
const canUpdateProgress = computed(() => props.status === ReadingStatus.STARTED)

const progressDraft = ref<string>(props.currentPage?.toString() ?? '')
const editingProgress = ref(false)

watch(
  () => props.currentPage,
  (val) => {
    progressDraft.value = val?.toString() ?? ''
    editingProgress.value = false
  },
)

function handleStart() {
  emit('start', {occurredAt: resolveOccurredAt()})
}

function handleFinish() {
  emit('finish', {occurredAt: resolveOccurredAt()})
}

function handleSaveProgress() {
  if (!canUpdateProgress.value || props.progressSaving) return
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
      <span class="status-label">{{ statusLabel }}</span>
      <span class="status-sep">·</span>
      <span class="status-subtitle">{{ statusSubtitle }}</span>
      <template v-if="canUpdateProgress">
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
          Update progress
        </button>
      </template>
    </div>
    <div v-if="canStart || canFinish" class="action-row">
      <input
        type="date"
        class="date-input"
        data-test="date-input"
        v-model="dateDraft"
        :max="todayIsoDate()"
      />
      <button
        v-if="canStart"
        class="btn-secondary btn-compact"
        type="button"
        data-test="start-reading"
        @click="handleStart"
        :disabled="updating"
      >
        Start Reading
      </button>
      <button
        v-if="canFinish"
        class="btn-primary btn-compact"
        type="button"
        data-test="finish-reading"
        @click="handleFinish"
        :disabled="updating"
      >
        Finish Reading
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
.action-row,
.progress-edit {
  display: flex;
  gap: var(--spacing-md);
  align-items: center;
  flex-wrap: wrap;
  font-size: 0.9rem;
}

.status-row {
  justify-content: space-between;
}

.status-row > .btn-link,
.status-row > .progress-edit {
  margin-left: auto;
}

.action-row {
  align-items: stretch;
}

.action-row .btn-compact {
  padding: 6px 14px;
}

input.date-input {
  align-self: stretch;
}

.status-label {
  font-weight: 600;
  color: var(--color-text);
}

.status-subtitle {
  color: var(--color-text-secondary);
}

.status-sep {
  color: var(--color-text-secondary);
  opacity: 0.5;
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

input.date-input {
  padding: 4px var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 0.9rem;
  width: auto;
  flex: 0 0 auto;
  display: inline-block;
}

.btn-compact {
  padding: 4px 10px;
  font-size: 0.9rem;
}

.btn-link {
  background: none;
  border: none;
  padding: 0;
  color: var(--color-primary);
  font-size: 0.9rem;
  cursor: pointer;
  align-self: flex-start;
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
