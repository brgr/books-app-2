<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import BookStatusPill from './BookStatusPill.vue'
import BookProgressBar from './BookProgressBar.vue'
import {ReadingStatus, type BookProgressUpdate} from '../../api/types'
import {formatShortDate} from '../../utils/date'

type ProgressUnit = 'page' | 'percent'

const props = defineProps<{
  status: ReadingStatus | null
  updating?: boolean
  currentPage?: number | null
  currentPercent?: number | null
  pageCount?: number | null
  startedAt?: string | null
  finishedAt?: string | null
  progressSaving?: boolean
}>()

const emit = defineEmits<{
  change: [status: ReadingStatus]
  'update-progress': [progress: BookProgressUpdate]
}>()

const hasPage = computed(
  () => props.currentPage !== null && props.currentPage !== undefined,
)
const hasPercent = computed(
  () => props.currentPercent !== null && props.currentPercent !== undefined,
)

// While actively reading, show the start date beside the pill ("since …")
// rather than in the bottom dates row, so the status and its timeline read
// together. Finished books keep their dates in the bottom row.
const showStartedInHeader = computed(
  () => props.status === ReadingStatus.STARTED && !!props.startedAt,
)

// The unit the user last tracked in, so re-opening the editor defaults to it.
const lastUnit = computed<ProgressUnit>(() => (hasPercent.value ? 'percent' : 'page'))

const progressUnit = ref<ProgressUnit>(lastUnit.value)
const progressDraft = ref<string>('')
const editingProgress = ref(false)

function currentValueFor(unit: ProgressUnit): string {
  const value = unit === 'percent' ? props.currentPercent : props.currentPage
  return value !== null && value !== undefined ? value.toString() : ''
}

watch(
  () => [props.currentPage, props.currentPercent],
  () => {
    editingProgress.value = false
  },
)

function selectUnit(unit: ProgressUnit) {
  if (unit === progressUnit.value) return
  progressUnit.value = unit
  progressDraft.value = currentValueFor(unit)
}

function handleSaveProgress() {
  if (props.progressSaving) return
  const trimmed = String(progressDraft.value ?? '').trim()
  if (!trimmed) {
    alert(progressUnit.value === 'percent' ? 'Please enter a percentage.' : 'Please enter a page number.')
    return
  }
  if (progressUnit.value === 'percent') {
    const percent = Number.parseFloat(trimmed)
    if (Number.isNaN(percent) || percent < 0 || percent > 100) {
      alert('Please enter a percentage between 0 and 100.')
      return
    }
    emit('update-progress', {percent})
    return
  }
  const page = Number.parseInt(trimmed, 10)
  if (Number.isNaN(page) || page < 0) {
    alert('Please enter a valid page number.')
    return
  }
  emit('update-progress', {page})
}

function handleProgressFocus(event: FocusEvent) {
  const target = event.target as HTMLInputElement | null
  target?.select()
}

function startEditingProgress() {
  progressUnit.value = lastUnit.value
  progressDraft.value = currentValueFor(progressUnit.value)
  editingProgress.value = true
}

function cancelEditingProgress() {
  editingProgress.value = false
}
</script>

<template>
  <div class="status-card" data-test="status-card">
    <div class="status-header">
      <BookStatusPill :status="status" :updating="updating ?? false" @change="emit('change', $event)" />
      <span v-if="showStartedInHeader" class="since">since {{ formatShortDate(startedAt ?? null) }}</span>
    </div>

    <BookProgressBar
      :current-page="currentPage"
      :current-percent="currentPercent"
      :page-count="pageCount"
    />

    <div class="progress-line">
      <span v-if="editingProgress" class="progress-edit">
        <span class="unit-toggle" role="group" aria-label="Progress unit">
          <button
            type="button"
            class="unit-btn"
            :class="{active: progressUnit === 'page'}"
            data-test="unit-page"
            :disabled="progressSaving"
            @click="selectUnit('page')"
          >
            Page
          </button>
          <button
            type="button"
            class="unit-btn"
            :class="{active: progressUnit === 'percent'}"
            data-test="unit-percent"
            :disabled="progressSaving"
            @click="selectUnit('percent')"
          >
            %
          </button>
        </span>
        <input
          v-model="progressDraft"
          type="number"
          min="0"
          :max="progressUnit === 'percent' ? 100 : undefined"
          :step="progressUnit === 'percent' ? 'any' : 1"
          inputmode="decimal"
          class="progress-input"
          data-test="progress-input"
          :disabled="progressSaving"
          :placeholder="progressUnit === 'percent' ? '%' : 'Page'"
          @focus="handleProgressFocus"
        />
        <span class="muted progress-suffix">
          <template v-if="progressUnit === 'page' && pageCount">of {{ pageCount }}</template>
          <template v-else-if="progressUnit === 'percent'">%</template>
        </span>
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
          <template v-if="hasPercent">{{ currentPercent }}%</template>
          <template v-else-if="hasPage">Page {{ currentPage }}<span v-if="pageCount"> of {{ pageCount }}</span></template>
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

    <div v-if="(startedAt && !showStartedInHeader) || finishedAt" class="dates">
      <span v-if="startedAt && !showStartedInHeader">Started {{ formatShortDate(startedAt) }}</span>
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

.status-header {
  display: flex;
  align-items: baseline;
  gap: var(--spacing-sm);
  flex-wrap: wrap;
}

.since {
  color: var(--color-text-secondary);
  font-size: 0.8rem;
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

.unit-toggle {
  display: inline-flex;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  overflow: hidden;
}

.unit-btn {
  background: none;
  border: none;
  padding: 4px var(--spacing-sm);
  color: var(--color-text-secondary);
  font-family: inherit;
  font-size: 0.85rem;
  cursor: pointer;
}

.unit-btn:not(:last-child) {
  border-right: 1px solid var(--color-border);
}

.unit-btn.active {
  background: var(--color-primary);
  color: #fff;
}

.unit-btn:disabled {
  cursor: not-allowed;
}

/* Reserve a fixed width so switching between "of {pages}" and "%" doesn't
   resize the fit-content card. */
.progress-suffix {
  min-width: 4rem;
  text-align: left;
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
