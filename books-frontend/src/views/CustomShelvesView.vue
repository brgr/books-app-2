<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { useRouter } from "vue-router";
import { createShelf, getShelves } from "../api/books";
import type { Shelf } from "../api/types";
import BookSearchModal from "../components/modals/BookSearchModal.vue";
import LibraryNav from "../components/ui/LibraryNav.vue";
import NavigationBar from "../components/ui/NavigationBar.vue";
import { cacheKeys } from "../cache/keys";
import { useAddBook } from "../composables/useAddBook";
import { useCachedQuery } from "../composables/useCachedQuery";

const router = useRouter();
const { data: shelves, error, refresh } = useCachedQuery<Shelf[]>(cacheKeys.shelves, getShelves);
const customShelves = computed(() => (shelves.value ?? []).filter((shelf) => shelf.ref.startsWith("custom:")));
const abandonedShelf = computed(() => (shelves.value ?? []).find((shelf) => shelf.ref === "reading:abandoned"));
const { showSearchModal, openSearch, closeSearch, selectBook } = useAddBook(refresh);
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
  if (creating.value) return;

  showCreateShelf.value = false;
  newShelfName.value = "";
  createError.value = "";
}

async function createNewShelf() {
  const name = newShelfName.value.trim();

  if (!name || creating.value) return;

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

function goTo(surface: "to-read" | "finished" | "shelves") {
  router.push(surface === "shelves" ? { name: "custom-shelves" } : { name: "shelf", params: { shelf: surface } });
}
</script>

<template>
  <div class="shelves-page">
    <NavigationBar @add-book="openSearch">
      <!-- TODO: We should move the `goTo` into LibraryNav directly... there's not reason that it doesn't know about this directly -->
      <template #nav><LibraryNav model-value="shelves" @update:model-value="goTo" /> </template
    ></NavigationBar>

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
          </button>
        </header>

        <section
          v-if="abandonedShelf && abandonedShelf.book_count > 0"
          class="reading-shelves"
          aria-label="Reading shelves"
        >
          <button
            type="button"
            class="shelf-row"
            @click="router.push({ name: 'shelf', params: { shelf: 'abandoned' } })"
          >
            <span>{{ abandonedShelf.display_name }}</span>
            <span>{{ abandonedShelf.book_count }} {{ abandonedShelf.book_count === 1 ? "book" : "books" }}</span>
          </button>
        </section>

        <div v-if="!customShelves.length" class="empty-state">No custom shelves yet. Create one to get started.</div>
        <div v-else class="shelf-list">
          <button
            v-for="shelf in customShelves"
            :key="shelf.ref"
            type="button"
            class="shelf-row"
            @click="router.push({ name: 'custom-shelf', params: { id: shelf.ref.slice('custom:'.length) } })"
          >
            <span>{{ shelf.display_name }}</span
            ><span>{{ shelf.book_count }} {{ shelf.book_count === 1 ? "book" : "books" }}</span>
          </button>
        </div>
      </template>
    </main>

    <BookSearchModal v-if="showSearchModal" @close="closeSearch" @select="selectBook" />
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
  margin-top: var(--spacing-xl);
}
.shelves-header h1 {
  margin: 0;
  font-size: 1.5rem;
}
.reading-shelves {
  margin-top: var(--spacing-lg);
}
.add-shelf-button {
  display: grid;
  box-sizing: border-box;
  width: 2.5rem;
  height: 2.5rem;
  place-items: center;
  padding: 0;
  border: none;
  border-radius: 50%;
  background: var(--color-primary);
  color: var(--color-bg-card);
  font: inherit;
  line-height: 1;
  cursor: pointer;
}
.add-shelf-button span {
  position: relative;
  width: 1rem;
  height: 1rem;
}
.add-shelf-button span::before,
.add-shelf-button span::after {
  position: absolute;
  top: 50%;
  left: 50%;
  width: 1rem;
  height: 2px;
  background: currentColor;
  content: "";
  transform: translate(-50%, -50%);
}
.add-shelf-button span::after {
  transform: translate(-50%, -50%) rotate(90deg);
}
.add-shelf-button:hover {
  border-color: transparent;
  filter: brightness(1.08);
}
.add-shelf-button:focus-visible {
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
  margin-top: var(--spacing-lg);
  display: flex;
  flex-direction: column;
  gap: var(--spacing-sm);
}
.shelf-row {
  display: flex;
  justify-content: space-between;
  width: 100%;
  padding: var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  background: var(--color-bg-card);
  color: var(--color-text);
  font: inherit;
  text-align: left;
  cursor: pointer;
}
.shelf-row span:last-child,
.empty-state {
  color: var(--color-text-secondary);
}
.empty-state,
.loading,
.error {
  padding: var(--spacing-xl);
  text-align: center;
}
.empty-state {
  margin-top: var(--spacing-lg);
}
@media (min-width: 769px) {
  .shelves-page {
    padding-bottom: var(--spacing-xl);
  }
}
</style>
