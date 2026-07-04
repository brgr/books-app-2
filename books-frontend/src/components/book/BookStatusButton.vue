<script setup lang="ts">
import {computed} from 'vue'
import {ReadingStatus} from '../../api/types'

const props = defineProps<{
  status: ReadingStatus | null
  updating: boolean
}>()

const emit = defineEmits<{
  change: [status: ReadingStatus]
}>()

type Action = {label: string; target: ReadingStatus}

// The single next action for the current status. Not-yet-started and abandoned
// books both offer "Start Reading"; a finished book can be read again.
const action = computed<Action>(() => {
  switch (props.status) {
    case ReadingStatus.STARTED:
      return {label: 'Finish', target: ReadingStatus.FINISHED}
    case ReadingStatus.FINISHED:
      return {label: 'Read Again', target: ReadingStatus.STARTED}
    default:
      return {label: 'Start Reading', target: ReadingStatus.STARTED}
  }
})

function activate() {
  if (props.updating) return
  emit('change', action.value.target)
}
</script>

<template>
  <button
    type="button"
    class="status-button"
    :disabled="updating"
    data-test="status-button"
    @click="activate"
  >
    {{ updating ? 'Saving…' : action.label }}
  </button>
</template>

<style scoped>
.status-button {
  display: inline-flex;
  align-items: center;
  padding: 8px 16px;
  border-radius: 999px;
  border: 1px solid var(--color-primary);
  background: var(--color-primary);
  color: #fff;
  font-size: 0.9rem;
  font-family: inherit;
  font-weight: 500;
  cursor: pointer;
  line-height: 1.2;
}

.status-button:hover:not(:disabled) {
  filter: brightness(1.1);
}

.status-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}
</style>
