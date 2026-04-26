<script setup lang="ts">
import {computed, ref, watch} from 'vue'
import {marked} from 'marked'

const props = defineProps<{
  notes: string
  saving: boolean
}>()

const emit = defineEmits<{
  save: [notes: string]
}>()

const editing = ref(false)
const draft = ref(props.notes)

watch(() => props.notes, (val) => {
  draft.value = val
  editing.value = false
})

const rendered = computed(() => {
  const raw = props.notes.trim()
  if (!raw) return ''
  return marked.parse(raw, {async: false, breaks: true, gfm: true}) as string
})

const dirty = computed(() => draft.value !== props.notes)

function startEditing() {
  draft.value = props.notes
  editing.value = true
}

function cancel() {
  draft.value = props.notes
  editing.value = false
}

function save() {
  if (!dirty.value || props.saving) return
  emit('save', draft.value)
}
</script>

<template>
  <div class="book-notes">
    <h2>Notes</h2>
    <template v-if="editing">
      <textarea
        v-model="draft"
        class="notes-textarea"
        rows="6"
        placeholder="Add your notes about this book... (Markdown supported)"
      ></textarea>
      <div class="notes-actions">
        <button
          type="button"
          class="btn-secondary"
          data-test="cancel"
          @click="cancel"
          :disabled="saving"
        >
          Cancel
        </button>
        <button
          class="btn-primary"
          data-test="save"
          @click="save"
          :disabled="saving || !dirty"
        >
          {{ saving ? 'Saving...' : 'Save Notes' }}
        </button>
      </div>
    </template>
    <template v-else>
      <div v-if="rendered" class="notes-rendered" v-html="rendered"></div>
      <p v-else class="notes-empty">No notes yet.</p>
      <div class="notes-actions">
        <button type="button" class="btn-secondary" data-test="edit" @click="startEditing">
          Update
        </button>
      </div>
    </template>
  </div>
</template>

<style scoped>
.book-notes {
  margin-bottom: var(--spacing-xl);
}

.book-notes h2 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

.notes-textarea {
  width: 100%;
  min-height: 120px;
  resize: vertical;
  padding: var(--spacing-sm);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  font-family: inherit;
  font-size: 0.95rem;
  line-height: 1.5;
}

.notes-actions {
  margin-top: var(--spacing-sm);
  display: flex;
  justify-content: flex-end;
  gap: var(--spacing-sm);
}

.notes-rendered {
  padding: var(--spacing-sm);
  border-radius: var(--border-radius);
  border: 1px solid var(--color-border);
  background: var(--color-bg);
  color: var(--color-text);
  line-height: 1.5;
}

.notes-rendered :first-child {
  margin-top: 0;
}

.notes-rendered :last-child {
  margin-bottom: 0;
}

.notes-empty {
  margin: 0;
  color: var(--color-text-muted, #888);
  font-style: italic;
}
</style>
