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
  close: []
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

watch(
  () => props.currentPage,
  (val) => { progressDraft.value = val?.toString() ?? '' },
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
</script>

<template>
  <div class="sheet-overlay" data-test="overlay" @click.self="emit('close')">
    <div class="sheet">
      <div class="sheet-header">
        <div>
          <h3>Reading status</h3>
          <p>{{ statusLabel }}</p>
        </div>
        <button class="sheet-close" type="button" data-test="close" @click="emit('close')">
          Close
        </button>
      </div>
      <div class="sheet-body">
        <p class="sheet-status-detail">{{ statusSubtitle }}</p>
        <div v-if="canUpdateProgress" class="sheet-progress-field">
          <span>Progress</span>
          <div class="sheet-progress-row">
            <input
              v-model="progressDraft"
              type="number"
              min="0"
              inputmode="numeric"
              pattern="[0-9]*"
              class="sheet-progress-input"
              data-test="progress-input"
              :disabled="progressSaving"
              placeholder="Page"
              @focus="handleProgressFocus"
            />
            <span v-if="pageCount" class="sheet-progress-total">of {{ pageCount }}</span>
            <button
              class="btn-secondary"
              type="button"
              data-test="save-progress"
              @click="handleSaveProgress"
              :disabled="progressSaving"
            >
              {{ progressSaving ? 'Saving...' : 'Save progress' }}
            </button>
          </div>
        </div>
        <label v-if="canStart || canFinish" class="sheet-date-field">
          <span>Date</span>
          <input
            type="date"
            data-test="date-input"
            v-model="dateDraft"
            :max="todayIsoDate()"
          />
        </label>
        <div class="sheet-actions">
          <button
            v-if="canStart"
            class="btn-secondary"
            type="button"
            data-test="start-reading"
            @click="handleStart"
            :disabled="updating"
          >
            Start Reading
          </button>
          <button
            v-if="canFinish"
            class="btn-primary"
            type="button"
            data-test="finish-reading"
            @click="handleFinish"
            :disabled="updating"
          >
            Finish Reading
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sheet-overlay {
  position: fixed;
  inset: 0;
  background: rgba(6, 6, 8, 0.55);
  display: flex;
  align-items: flex-end;
  justify-content: center;
  z-index: 50;
  backdrop-filter: blur(6px);
}

.sheet {
  width: min(480px, 96vw);
  background: #1a141f;
  border-radius: 20px 20px 0 0;
  padding: var(--spacing-lg);
  box-shadow: 0 -20px 40px rgba(6, 6, 8, 0.45);
  border: 1px solid rgba(255, 255, 255, 0.08);
}

.sheet-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}

.sheet-header h3 {
  margin: 0;
  font-size: 1.1rem;
}

.sheet-header p {
  margin: 4px 0 0 0;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.sheet-close {
  border: none;
  background: rgba(255, 255, 255, 0.08);
  color: var(--color-text);
  padding: 6px 12px;
  border-radius: 999px;
  cursor: pointer;
}

.sheet-body {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.sheet-status-detail {
  margin: 0;
  font-size: 0.95rem;
  color: var(--color-text-secondary);
}

.sheet-actions {
  display: flex;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.sheet-date-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.sheet-progress-field {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  font-size: 0.9rem;
  color: var(--color-text-secondary);
}

.sheet-progress-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  flex-wrap: wrap;
}

.sheet-progress-input {
  width: 80px;
  padding: var(--spacing-xs) var(--spacing-sm);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  font-size: 1rem;
  appearance: textfield;
  -moz-appearance: textfield;
}

.sheet-progress-input::-webkit-outer-spin-button,
.sheet-progress-input::-webkit-inner-spin-button {
  margin: 0;
  -webkit-appearance: none;
}

.sheet-progress-total {
  color: var(--color-text-secondary);
  font-size: 0.95rem;
}

.sheet-date-field input {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--radius-sm);
  background: var(--color-bg);
  color: var(--color-text);
  font-size: 1rem;
}
</style>
