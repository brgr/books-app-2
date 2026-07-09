<script lang="ts" setup>
import { ref } from "vue";
import { stagePendingCover } from "../book/pendingCoverUploads.ts";

const emit = defineEmits<{
  select: [imageUrl: string];
}>();

const error = ref("");
const dragActive = ref(false);
const imageUrl = ref("");
const ALLOWED = ["image/jpeg", "image/png", "image/webp", "image/gif"];
const MAX_BYTES = 10 * 1024 * 1024;

function acceptFile(file: File | undefined) {
  if (!file) return;

  if (!ALLOWED.includes(file.type)) {
    error.value = "Unsupported file type. Use a JPEG, PNG, WebP, or GIF image.";
    return;
  }
  if (file.size > MAX_BYTES) {
    error.value = "That image is too large (max 10 MB).";
    return;
  }

  error.value = "";
  // Staged locally; the bytes are only uploaded when the book is saved.
  emit("select", stagePendingCover(file));
}

function handleFile(event: Event) {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0];
  input.value = ""; // allow re-picking the same file
  acceptFile(file);
}

function handleDrop(event: DragEvent) {
  dragActive.value = false;
  acceptFile(event.dataTransfer?.files?.[0]);
}

function acceptUrl() {
  const url = imageUrl.value.trim();
  if (!url) return;
  if (!/^https?:\/\//i.test(url)) {
    error.value = "Enter a full image URL starting with http:// or https://.";
    return;
  }
  error.value = "";
  // The URL is downloaded and stored server-side when the book is saved.
  emit("select", url);
}
</script>

<template>
  <div class="upload-tab">
    <label
      class="dropzone"
      :class="{ 'drag-active': dragActive }"
      @dragenter.prevent="dragActive = true"
      @dragover.prevent="dragActive = true"
      @dragleave.prevent="dragActive = false"
      @drop.prevent="handleDrop"
    >
      <input accept="image/jpeg,image/png,image/webp,image/gif" type="file" @change="handleFile" />
      <span class="dropzone-title">Drop an image here, or click to choose</span>
      <span class="dropzone-hint">JPEG, PNG, WebP, or GIF · up to 10 MB</span>
    </label>

    <div class="or-divider"><span>or paste an image URL</span></div>

    <div class="url-row">
      <input v-model="imageUrl" type="url" placeholder="https://example.com/cover.jpg" @keyup.enter="acceptUrl" />
      <button type="button" class="btn-primary" :disabled="!imageUrl.trim()" @click="acceptUrl">Use URL</button>
    </div>

    <p class="mode-hint">Nothing is sent until you save the book.</p>
    <div v-if="error" class="error">{{ error }}</div>
  </div>
</template>

<style scoped>
.upload-tab {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}

.dropzone {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  padding: var(--spacing-xl);
  border: 1px dashed var(--color-border);
  border-radius: var(--border-radius);
  background-color: var(--color-bg-card);
  cursor: pointer;
  text-align: center;
  transition: border-color 0.15s ease;
}

.dropzone:hover,
.dropzone.drag-active {
  border-color: var(--color-primary);
}

.dropzone.drag-active {
  background-color: var(--color-bg);
}

.dropzone input {
  display: none;
}

.dropzone-title {
  color: var(--color-text);
  font-weight: 600;
}

.dropzone-hint {
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

.or-divider {
  display: flex;
  align-items: center;
  gap: var(--spacing-sm);
  color: var(--color-text-secondary);
  font-size: 0.85rem;
}

.or-divider::before,
.or-divider::after {
  content: "";
  flex: 1;
  height: 1px;
  background-color: var(--color-border);
}

.url-row {
  display: flex;
  gap: var(--spacing-sm);
}

.url-row input {
  flex: 1;
  min-width: 0;
}

.mode-hint {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}
</style>
