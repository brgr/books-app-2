<script setup lang="ts">
import { nextTick, ref } from "vue";
import NavigationBar from "../components/navigation/NavigationBar.vue";
import GoogleBookSearchForm from "../components/book/GoogleBookSearchForm.vue";
import ManualBookForm from "../components/book/ManualBookForm.vue";

type EntryMode = "search" | "manual";
const entryMode = ref<EntryMode>("search");
const searchTab = ref<HTMLButtonElement>();
const manualTab = ref<HTMLButtonElement>();

function selectMode(mode: EntryMode) {
  entryMode.value = mode;
}

async function handleTabKeydown(event: KeyboardEvent) {
  if (!["ArrowLeft", "ArrowRight", "Home", "End"].includes(event.key)) {
    return;
  }

  event.preventDefault();

  let mode: EntryMode = entryMode.value === "search" ? "manual" : "search";
  if (event.key === "Home") {
    mode = "search";
  } else if (event.key === "End") {
    mode = "manual";
  }

  selectMode(mode);

  await nextTick();

  (entryMode.value === "search" ? searchTab.value : manualTab.value)?.focus();
}
</script>

<template>
  <div class="book-add-view">
    <NavigationBar />
    <main class="container-narrow">
      <div class="page-header">
        <h1>Add book</h1>

        <RouterLink :to="{ name: 'books' }" class="btn btn-small">Cancel</RouterLink>
      </div>

      <div class="mode-tabs" role="tablist" aria-label="Add book method" @keydown="handleTabKeydown">
        <button
          id="book-add-search-tab"
          ref="searchTab"
          type="button"
          role="tab"
          class="mode-tab"
          aria-controls="book-add-search-panel"
          :aria-selected="entryMode === 'search'"
          :tabindex="entryMode === 'search' ? 0 : -1"
          @click="selectMode('search')"
        >
          Search
        </button>
        <button
          id="book-add-manual-tab"
          ref="manualTab"
          type="button"
          role="tab"
          class="mode-tab"
          aria-controls="book-add-manual-panel"
          :aria-selected="entryMode === 'manual'"
          :tabindex="entryMode === 'manual' ? 0 : -1"
          @click="selectMode('manual')"
        >
          Manual
        </button>
      </div>

      <div
        v-show="entryMode === 'search'"
        id="book-add-search-panel"
        role="tabpanel"
        aria-labelledby="book-add-search-tab"
      >
        <GoogleBookSearchForm />
      </div>

      <div
        v-show="entryMode === 'manual'"
        id="book-add-manual-panel"
        role="tabpanel"
        aria-labelledby="book-add-manual-tab"
      >
        <ManualBookForm />
      </div>
    </main>
  </div>
</template>

<style scoped>
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-lg);
}

.mode-tabs {
  display: flex;
  gap: var(--spacing-lg);
  margin-bottom: var(--spacing-lg);
}

.mode-tab {
  padding: var(--spacing-sm) 0;
  border: none;
  border-bottom: 2px solid transparent;
  border-radius: 0;
  background: none;
  color: var(--color-text-secondary);
}

.mode-tab[aria-selected="true"] {
  border-bottom-color: var(--color-primary);
  color: var(--color-primary);
}

.mode-tab:hover:not(:disabled) {
  background: none;
  color: var(--color-primary);
}

.mode-tab:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 4px;
}
</style>
