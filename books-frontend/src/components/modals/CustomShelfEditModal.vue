<script setup lang="ts">
import { nextTick, onMounted, ref } from "vue";

const props = defineProps<{
  shelfName: string;
  saving: boolean;
  error: string;
}>();

const emit = defineEmits<{
  close: [];
  rename: [name: string];
  requestDelete: [];
  delete: [];
}>();

const mode = ref<"edit" | "delete">("edit");
const name = ref(props.shelfName);
const nameInput = ref<HTMLInputElement | null>(null);

async function focusNameInput() {
  await nextTick();
  nameInput.value?.focus();
  nameInput.value?.select();
}

onMounted(focusNameInput);

function close() {
  if (!props.saving) emit("close");
}

function submitRename() {
  const trimmedName = name.value.trim();
  if (trimmedName && !props.saving) emit("rename", trimmedName);
}

function showDeleteConfirmation() {
  mode.value = "delete";
  emit("requestDelete");
}
</script>

<template>
  <Teleport to="body">
    <div class="modal-overlay" @click.self="close">
      <div
        v-if="mode === 'edit'"
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="edit-shelf-title"
        @keydown.esc="close"
      >
        <div class="modal-header">
          <h3 id="edit-shelf-title">Edit shelf</h3>
          <button type="button" class="btn-small" :disabled="saving" @click="close">Close</button>
        </div>

        <form @submit.prevent="submitRename">
          <div class="modal-body">
            <label for="shelf-name">Shelf name</label>
            <input id="shelf-name" ref="nameInput" v-model="name" maxlength="100" :disabled="saving" />
            <p v-if="error" class="action-error">{{ error }}</p>
          </div>

          <div class="modal-footer">
            <button type="button" class="btn-danger" :disabled="saving" @click="showDeleteConfirmation">
              Delete shelf
            </button>
            <button type="button" :disabled="saving" @click="close">Cancel</button>
            <button type="submit" class="btn-primary" :disabled="!name.trim() || saving">
              {{ saving ? "Saving…" : "Save" }}
            </button>
          </div>
        </form>
      </div>

      <div
        v-else
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="delete-shelf-title"
        @keydown.esc="close"
      >
        <div class="modal-header"><h3 id="delete-shelf-title">Delete shelf?</h3></div>
        <div class="modal-body">
          <p>Delete “{{ shelfName }}”? Its books will remain in your library.</p>
          <p v-if="error" class="action-error">{{ error }}</p>
        </div>
        <div class="modal-footer">
          <button type="button" :disabled="saving" @click="close">Cancel</button>
          <button type="button" class="btn-danger" :disabled="saving" @click="emit('delete')">
            {{ saving ? "Deleting…" : "Delete shelf" }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.modal-body label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
}
.modal-body input {
  box-sizing: border-box;
  width: 100%;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg-card);
  color: var(--color-text);
  font: inherit;
}
.action-error {
  margin: var(--spacing-sm) 0 0;
  color: var(--color-danger, #c0392b);
}
</style>
