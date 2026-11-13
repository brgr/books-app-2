<script setup lang="ts">
import { computed } from "vue";
import { marked } from "marked";
import DOMPurify from "dompurify";

defineProps<{
  editing: boolean;
  disabled?: boolean;
}>();

const notes = defineModel<string>({ required: true });

const emit = defineEmits<{
  submit: [];
}>();

const renderedNotes = computed(() => {
  const raw = notes.value.trim();

  if (!raw) {
    return "";
  }

  return DOMPurify.sanitize(marked.parse(raw, { async: false, breaks: true, gfm: true }), {
    USE_PROFILES: { html: true },
  });
});
</script>

<template>
  <textarea
    v-if="editing"
    v-model="notes"
    class="notes-textarea"
    rows="6"
    aria-label="Notes"
    placeholder="Your notes about this book."
    :disabled="disabled"
    @keydown.ctrl.enter.prevent="emit('submit')"
  ></textarea>
  <!-- eslint-disable-next-line vue/no-v-html -- renderedNotes is sanitized with DOMPurify -->
  <div v-else-if="renderedNotes" class="notes-rendered" v-html="renderedNotes"></div>
  <p v-else class="notes-empty">No notes yet.</p>
</template>

<style scoped>
.notes-textarea {
  width: 100%;
  min-height: 120px;
  resize: vertical;
  padding: 0;
  border: none;
  background: none;
  color: var(--color-text);
  font-family: inherit;
  line-height: 1.5;
}

.notes-textarea:focus {
  outline: none;
}

.notes-rendered {
  color: var(--color-text);
  line-height: 1.5;
}

.notes-rendered :deep(blockquote) {
  margin: var(--spacing-md) 0;
  padding: var(--spacing-sm) var(--spacing-md);
  border-inline-start: 3px solid var(--color-primary);
  background: var(--color-bg-card);
  overflow-wrap: anywhere;
}

.notes-rendered :deep(> :first-child),
.notes-rendered :deep(blockquote > :first-child) {
  margin-top: 0;
}

.notes-rendered :deep(> :last-child),
.notes-rendered :deep(blockquote > :last-child) {
  margin-bottom: 0;
}

.notes-empty {
  margin: 0;
  color: var(--color-text-muted, #888);
  font-style: italic;
}
</style>
