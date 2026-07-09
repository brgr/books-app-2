<script lang="ts" setup>
import { computed, onBeforeUnmount, ref } from "vue";
import { getMediaUrl } from "../../api/client";
import { discardPendingCover, isPendingCover } from "./pendingCoverUploads";
import CoverModal from "../modals/CoverModal.vue";

const props = defineProps<{
  modelValue: string;
  title: string;
  author: string;
  isbn: string;
  bookId?: number;
  disabled?: boolean;
}>();

const emit = defineEmits<{
  (e: "update:modelValue", value: string): void;
}>();

const showCoverModal = ref(false);

// Google Books sometimes returns an "image not available" placeholder at higher zoom levels for metadata-only volumes.
// The zoom=1 thumbnail is therefore the more reliable image, so we preview that.
function previewSafeUrl(value: string): string {
  if (value.includes("books.google") && /[?&]zoom=[2-9]/.test(value)) {
    return value.replace(/zoom=\d+/, "zoom=1");
  }
  return value;
}

const previewUrl = computed(() => getMediaUrl(previewSafeUrl(props.modelValue)));

// The upgrade search runs against the stored cover; a locally-staged upload isn't stored yet.
const canUpgrade = computed(
  () => !!props.modelValue && !props.modelValue.startsWith("http") && !isPendingCover(props.modelValue),
);

function replaceCover(imageUrl: string) {
  // Drop a previously staged upload we're about to replace, so its object URL isn't leaked.
  if (props.modelValue !== imageUrl) discardPendingCover(props.modelValue);
  emit("update:modelValue", imageUrl);
}

function handleCoverSelected(imageUrl: string) {
  replaceCover(imageUrl);
  showCoverModal.value = false;
}

// A staged upload that's never saved should not outlive the form.
onBeforeUnmount(() => discardPendingCover(props.modelValue));
</script>

<template>
  <div class="form-group">
    <label>Cover</label>
    <div class="cover-row">
      <div :class="{ empty: !modelValue }" class="cover-preview">
        <img v-if="previewUrl" :src="previewUrl" alt="Cover preview" />
        <span v-else>No cover</span>
      </div>
      <div class="cover-actions">
        <span v-if="!modelValue" class="cover-status">No cover</span>
        <div class="cover-buttons">
          <button :disabled="disabled" type="button" @click="showCoverModal = true">
            {{ modelValue ? "Change cover" : "Find cover" }}
          </button>
          <button v-if="modelValue" :disabled="disabled" class="btn-small" type="button" @click="replaceCover('')">
            Clear
          </button>
        </div>
      </div>
    </div>

    <CoverModal
      v-if="showCoverModal"
      :book-id="bookId"
      :can-upgrade="canUpgrade"
      :initial-author="author"
      :initial-isbn="isbn"
      :initial-title="title"
      @close="showCoverModal = false"
      @select="handleCoverSelected"
    />
  </div>
</template>

<style scoped>
.cover-row {
  display: flex;
  gap: var(--spacing-md);
  align-items: flex-start;
}

.cover-preview {
  width: 120px;
  aspect-ratio: 2 / 3;
  flex-shrink: 0;
  border-radius: var(--border-radius);
  background-color: var(--color-bg);
  border: 1px solid var(--color-border);
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--color-text-secondary);
  font-size: 12px;
}

.cover-preview img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.cover-actions {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
  min-width: 0;
}

.cover-status {
  color: var(--color-text-secondary);
  font-size: 0.9rem;
}

.cover-buttons {
  display: flex;
  gap: var(--spacing-sm);
}
</style>
