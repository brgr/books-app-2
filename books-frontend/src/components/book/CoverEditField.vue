<script setup lang="ts">
import { ref, computed } from "vue";
import { getMediaUrl } from "../../api/client";
import CoverPickerModal from "../modals/CoverPickerModal.vue";
import CoverUpgradeModal from "../modals/CoverUpgradeModal.vue";

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

const showCoverPicker = ref(false);
const showCoverUpgrade = ref(false);

const previewUrl = computed(() => getMediaUrl(props.modelValue));

const canUpgrade = computed(() => !!props.modelValue && !props.modelValue.startsWith("http"));

function handleCoverSelected(imageUrl: string) {
  emit("update:modelValue", imageUrl);
  showCoverPicker.value = false;
}

function handleUpgradeSelected(imageUrl: string) {
  emit("update:modelValue", imageUrl);
  showCoverUpgrade.value = false;
}
</script>

<template>
  <div class="form-group">
    <label>Cover</label>
    <div class="cover-row">
      <div class="cover-preview" :class="{ empty: !modelValue }">
        <img v-if="previewUrl" :src="previewUrl" alt="Cover preview" />
        <span v-else>No cover</span>
      </div>
      <div class="cover-actions">
        <span v-if="!modelValue" class="cover-status">No cover</span>
        <div class="cover-buttons">
          <button type="button" @click="showCoverPicker = true" :disabled="disabled">Find cover</button>
          <button type="button" v-if="canUpgrade" @click="showCoverUpgrade = true" :disabled="disabled">
            Upgrade cover
          </button>
          <button
            type="button"
            v-if="modelValue"
            @click="emit('update:modelValue', '')"
            :disabled="disabled"
            class="btn-small"
          >
            Clear
          </button>
        </div>
      </div>
    </div>

    <CoverPickerModal
      v-if="showCoverPicker"
      :initial-title="title"
      :initial-author="author"
      :initial-isbn="isbn"
      @select="handleCoverSelected"
      @close="showCoverPicker = false"
    />

    <CoverUpgradeModal
      v-if="showCoverUpgrade && bookId"
      :book-id="bookId"
      @select="handleUpgradeSelected"
      @close="showCoverUpgrade = false"
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
