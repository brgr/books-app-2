<script setup lang="ts">
import { ref } from "vue";
import CoverSearchTab from "./CoverSearchTab.vue";
import CoverUpgradeTab from "./CoverUpgradeTab.vue";

const props = defineProps<{
  initialTitle?: string;
  initialAuthor?: string;
  initialIsbn?: string;
  bookId?: number;
  canUpgrade?: boolean;
}>();

const emit = defineEmits<{
  close: [];
  select: [imageUrl: string];
}>();

const showUpgradeTab = Boolean(props.bookId && props.canUpgrade);
const mode = ref<"search" | "upgrade">("search");
// The upgrade tab starts a background job on mount, so only mount it once opened.
const upgradeActivated = ref(false);

function selectMode(next: "search" | "upgrade") {
  mode.value = next;
  if (next === "upgrade") upgradeActivated.value = true;
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h3>Change Cover</h3>
        <button @click="emit('close')" class="btn-small">Close</button>
      </div>

      <div v-if="showUpgradeTab" class="tabs">
        <button type="button" class="tab" :class="{ active: mode === 'search' }" @click="selectMode('search')">
          Search
        </button>
        <button type="button" class="tab" :class="{ active: mode === 'upgrade' }" @click="selectMode('upgrade')">
          Higher resolution
        </button>
      </div>

      <div class="modal-body">
        <CoverSearchTab
          v-show="mode === 'search'"
          :initial-title="initialTitle"
          :initial-author="initialAuthor"
          :initial-isbn="initialIsbn"
          @select="emit('select', $event)"
        />
        <CoverUpgradeTab
          v-if="upgradeActivated && bookId"
          v-show="mode === 'upgrade'"
          :book-id="bookId"
          @select="emit('select', $event)"
        />
      </div>
    </div>
  </div>
</template>

<style scoped>
.tabs {
  display: flex;
  gap: var(--spacing-xs);
  padding: 0 var(--spacing-md);
  border-bottom: 1px solid var(--color-border);
}

.tab {
  background: none;
  border: none;
  border-bottom: 2px solid transparent;
  padding: var(--spacing-sm) var(--spacing-md);
  margin-bottom: -1px;
  color: var(--color-text-secondary);
  font-size: 0.9rem;
  cursor: pointer;
}

.tab:hover {
  color: var(--color-text);
}

.tab.active {
  color: var(--color-primary);
  border-bottom-color: var(--color-primary);
}
</style>
