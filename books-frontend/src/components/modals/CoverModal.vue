<script lang="ts" setup>
import { ref } from "vue";
import CoverSearchTab from "./CoverSearchTab.vue";
import CoverUpgradeTab from "./CoverUpgradeTab.vue";
import CoverUploadTab from "./CoverUploadTab.vue";

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

type Mode = "search" | "upload" | "upgrade";

const showUpgradeTab = Boolean(props.bookId && props.canUpgrade);
const mode = ref<Mode>("search");
// The upgrade tab starts a background job on mount, so only mount it once opened.
const upgradeActivated = ref(false);

function selectMode(next: Mode) {
  mode.value = next;
  if (next === "upgrade") upgradeActivated.value = true;
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal">
      <div class="modal-header">
        <h3>Change Cover</h3>
        <button class="btn-small" @click="emit('close')">Close</button>
      </div>

      <div class="tabs">
        <button :class="{ active: mode === 'search' }" class="tab" type="button" @click="selectMode('search')">
          Search
        </button>
        <button :class="{ active: mode === 'upload' }" class="tab" type="button" @click="selectMode('upload')">
          Upload
        </button>
        <button
          v-if="showUpgradeTab"
          :class="{ active: mode === 'upgrade' }"
          class="tab"
          type="button"
          @click="selectMode('upgrade')"
        >
          Higher resolution
        </button>
      </div>

      <div class="modal-body">
        <!-- Wrap each tab in its own element: these components have multiple root nodes,
             so v-show on the component itself can't hide them. -->
        <div v-show="mode === 'search'">
          <CoverSearchTab
            :initial-author="initialAuthor"
            :initial-isbn="initialIsbn"
            :initial-title="initialTitle"
            @select="emit('select', $event)"
          />
        </div>
        <div v-show="mode === 'upload'">
          <CoverUploadTab @select="emit('select', $event)" />
        </div>
        <div v-if="upgradeActivated && bookId" v-show="mode === 'upgrade'">
          <CoverUpgradeTab :book-id="bookId" @select="emit('select', $event)" />
        </div>
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
