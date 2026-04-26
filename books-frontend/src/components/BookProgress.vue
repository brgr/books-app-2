<script setup lang="ts">
import {computed, ref, watch} from 'vue'

const props = defineProps<{
  currentPage: number | null
  pageCount: number | null
  canUpdate: boolean
  saving: boolean
}>()

const emit = defineEmits<{
  save: [page: number]
}>()

const editing = ref(false)
const draft = ref<string | number>(props.currentPage?.toString() ?? '')

watch(() => props.currentPage, (val) => {
  draft.value = val?.toString() ?? ''
  editing.value = false
})

const summary = computed(() => {
  if (props.currentPage === null || props.currentPage === undefined) {
    return 'No progress yet'
  }
  if (props.pageCount) {
    return `Page ${props.currentPage} of ${props.pageCount}`
  }
  return `Page ${props.currentPage}`
})

function startEditing() {
  draft.value = props.currentPage?.toString() ?? ''
  editing.value = true
}

function cancel() {
  draft.value = props.currentPage?.toString() ?? ''
  editing.value = false
}

function save() {
  if (!props.canUpdate || props.saving) return
  const trimmed = String(draft.value ?? '').trim()
  if (!trimmed) {
    alert('Please enter a page number.')
    return
  }
  const page = Number.parseInt(trimmed, 10)
  if (Number.isNaN(page) || page < 0) {
    alert('Please enter a valid page number.')
    return
  }
  emit('save', page)
}

function handleFocus(event: FocusEvent) {
  const target = event.target as HTMLInputElement | null
  target?.select()
}
</script>

<template>
  <div class="progress-inline">
    <span class="progress-label">Progress</span>
    <div v-if="editing" class="progress-row">
      <input
        v-model="draft"
        type="number"
        min="0"
        inputmode="numeric"
        pattern="[0-9]*"
        class="progress-input"
        :disabled="!canUpdate || saving"
        placeholder="Page"
        @focus="handleFocus"
      />
      <span v-if="pageCount" class="progress-total">of {{ pageCount }}</span>
      <button
        class="progress-button"
        data-test="save"
        @click="save"
        :disabled="!canUpdate || saving"
      >
        {{ saving ? 'Saving...' : 'Save' }}
      </button>
      <button
        class="progress-button progress-cancel"
        type="button"
        data-test="cancel"
        @click="cancel"
        :disabled="saving"
      >
        Cancel
      </button>
    </div>
    <div v-else class="progress-row">
      <span class="progress-text">{{ summary }}</span>
      <button
        class="progress-button"
        data-test="update"
        @click="startEditing"
        :disabled="!canUpdate || saving"
      >
        Update
      </button>
    </div>
    <p v-if="!canUpdate" class="progress-hint">
      Start reading to track progress.
    </p>
  </div>
</template>

<style scoped>
.progress-inline {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
  margin-bottom: var(--spacing-lg);
}

.progress-label {
  font-size: 0.95rem;
  font-weight: 600;
  color: var(--color-text);
}

.progress-row {
  display: flex;
  gap: var(--spacing-sm);
  align-items: center;
  flex-wrap: wrap;
}

.progress-input {
  width: 54px;
  padding: var(--spacing-xs) var(--spacing-sm);
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

.progress-text {
  color: var(--color-text);
  font-size: 0.95rem;
}

.progress-button {
  padding: 0;
  border: none;
  background: none;
  color: var(--color-primary);
  font-size: 0.9rem;
  cursor: pointer;
}

.progress-button:disabled {
  color: var(--color-text-secondary);
  cursor: not-allowed;
}

.progress-cancel {
  color: var(--color-danger);
}

.progress-cancel:disabled {
  color: var(--color-text-secondary);
}

.progress-hint {
  margin-top: var(--spacing-xs);
  color: var(--color-text-secondary);
  font-size: 12px;
}

@media (max-width: 768px) {
  .progress-inline {
    align-items: center;
  }

  .progress-row {
    justify-content: center;
  }
}
</style>
