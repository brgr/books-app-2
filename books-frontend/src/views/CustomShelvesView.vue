<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { useRouter } from "vue-router";
import { createShelf, getShelves } from "../api/books";
import type { Shelf } from "../api/types";
import NavigationBar from "../components/navigation/NavigationBar.vue";
import { cacheKeys } from "../cache/keys";
import { useCachedQuery } from "../composables/useCachedQuery";

const router = useRouter();
const { data: shelves, error, refresh } = useCachedQuery<Shelf[]>(cacheKeys.shelves, getShelves);
const customShelves = computed(() => (shelves.value ?? []).filter((shelf) => shelf.ref.startsWith("custom:")));
const abandonedShelf = computed(() => (shelves.value ?? []).find((shelf) => shelf.ref === "reading:abandoned"));
const shelvesToDisplay = computed(() => [
  ...(abandonedShelf.value && abandonedShelf.value.book_count > 0 ? [abandonedShelf.value] : []),
  ...customShelves.value,
]);
const showCreateShelf = ref(false);
const newShelfName = ref("");
const creating = ref(false);
const createError = ref("");
const newShelfNameInput = ref<HTMLInputElement | null>(null);

async function openCreateShelf() {
  showCreateShelf.value = true;
  await nextTick();
  newShelfNameInput.value?.focus();
}

function closeCreateShelf() {
  if (creating.value) {
    return;
  }

  showCreateShelf.value = false;
  newShelfName.value = "";
  createError.value = "";
}

async function createNewShelf() {
  const name = newShelfName.value.trim();

  if (!name || creating.value) {
    return;
  }

  creating.value = true;
  createError.value = "";

  try {
    const shelf = await createShelf(name);
    newShelfName.value = "";
    showCreateShelf.value = false;

    await refresh();
    await router.push({ name: "custom-shelf", params: { id: shelf.ref.slice("custom:".length) } });
  } catch (error) {
    console.error("Failed to create shelf:", error);
    createError.value = error instanceof Error ? error.message : "Failed to create shelf.";
  } finally {
    creating.value = false;
  }
}
</script>

<template>
  <div class="shelves-page">
    <NavigationBar />

    <main class="container">
      <div v-if="error" class="error">Failed to load shelves. Please try again.</div>
      <div v-else-if="!shelves" class="loading">Loading shelves...</div>
      <template v-else>
        <header class="shelves-header">
          <h1>My shelves</h1>
          <button
            type="button"
            class="add-shelf-button"
            aria-label="Create a new shelf"
            title="Create a new shelf"
            @click="openCreateShelf"
          >
            <span aria-hidden="true">+</span>
            New shelf
          </button>
        </header>

        <div v-if="shelvesToDisplay.length" class="shelf-list">
          <RouterLink
            v-for="shelf in shelvesToDisplay"
            :key="shelf.ref"
            class="shelf-row"
            :to="
              shelf.ref === 'reading:abandoned'
                ? { name: 'shelf', params: { shelf: 'abandoned' } }
                : { name: 'custom-shelf', params: { id: shelf.ref.slice('custom:'.length) } }
            "
          >
            <span class="shelf-details">
              <span class="shelf-name">{{ shelf.display_name }}</span>
              <span class="shelf-count">{{ shelf.book_count }} {{ shelf.book_count === 1 ? "book" : "books" }}</span>
            </span>
            <span class="shelf-chevron" aria-hidden="true">›</span>
          </RouterLink>
        </div>
        <div v-if="!customShelves.length" class="empty-state">No custom shelves yet. Create one to get started.</div>
      </template>
    </main>

    <Teleport to="body">
      <div v-if="showCreateShelf" class="modal-overlay" @click.self="closeCreateShelf">
        <div
          class="modal"
          role="dialog"
          aria-modal="true"
          aria-labelledby="new-shelf-title"
          @keydown.esc="closeCreateShelf"
        >
          <div class="modal-header">
            <h3 id="new-shelf-title">New shelf</h3>
            <button type="button" class="btn-small" :disabled="creating" @click="closeCreateShelf">Close</button>
          </div>
          <form class="create-shelf" @submit.prevent="createNewShelf">
            <div class="modal-body">
              <label for="new-shelf-name">Shelf name</label>
              <input
                id="new-shelf-name"
                ref="newShelfNameInput"
                v-model="newShelfName"
                maxlength="100"
                placeholder="e.g. Favourite sci-fi"
                :disabled="creating"
              />
              <p v-if="createError" class="create-error">{{ createError }}</p>
            </div>
            <div class="modal-footer">
              <button type="button" :disabled="creating" @click="closeCreateShelf">Cancel</button>
              <button type="submit" class="btn-primary" :disabled="!newShelfName.trim() || creating">
                {{ creating ? "Creating…" : "Create shelf" }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.shelves-page {
  min-height: 100svh;
  padding-bottom: 112px;
  background: var(--color-bg);
}
.shelves-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin: var(--spacing-sm) 0 var(--spacing-lg);
}
.shelves-header h1 {
  margin: 0;
  font-size: 1.5rem;
}
.add-shelf-button {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  white-space: nowrap;
}
.add-shelf-button span {
  font-size: 1.125rem;
  line-height: 1;
}
.add-shelf-button:focus-visible,
.shelf-row:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 3px;
}
.create-shelf label {
  display: block;
  margin-bottom: var(--spacing-sm);
  font-weight: 600;
}
.create-shelf input {
  box-sizing: border-box;
  width: 100%;
  padding: 0.65rem 0.75rem;
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg-card);
  color: var(--color-text);
  font: inherit;
}
.create-error {
  margin: var(--spacing-sm) 0 0;
  color: var(--color-danger, #c0392b);
}
.shelf-list {
  display: flex;
  flex-direction: column;
  border: 1px solid var(--color-border);
  border-radius: 6px;
}
.shelf-row {
  display: flex;
  align-items: center;
  gap: var(--spacing-md);
  min-width: 0;
  width: 100%;
  min-height: 56px;
  padding: var(--spacing-md);
  color: var(--color-text);
  text-decoration: none;
  transition: background-color 0.15s ease;
}
.shelf-row:hover {
  background: color-mix(in srgb, var(--color-primary) 6%, var(--color-bg-card));
}
.shelf-details {
  display: flex;
  align-items: center;
  flex: 1;
  min-width: 0;
  gap: var(--spacing-md);
}
.shelf-name {
  flex: 1;
  min-width: 0;
  font-weight: 600;
  overflow-wrap: anywhere;
}
.shelf-count {
  flex: none;
  font-size: 0.8125rem;
  white-space: nowrap;
}
.shelf-count,
.shelf-chevron,
.empty-state {
  color: var(--color-text-secondary);
}
.shelf-chevron {
  flex: none;
  font-size: 1.25rem;
  line-height: 1;
}
.shelf-row + .shelf-row {
  border-top: 1px solid var(--color-border);
}
.shelf-row:first-child {
  border-top-left-radius: 5px;
  border-top-right-radius: 5px;
}
.shelf-row:last-child {
  border-bottom-left-radius: 5px;
  border-bottom-right-radius: 5px;
}
.empty-state,
.loading,
.error {
  padding: var(--spacing-xl);
  text-align: center;
}
@media (min-width: 769px) {
  .shelves-page {
    padding-bottom: var(--spacing-xl);
  }
}
</style>
