<script setup lang="ts">
import { computed, nextTick, ref } from "vue";
import { RouterLink } from "vue-router";
import { addBookToShelf, getBookShelves, getShelves, removeBookFromShelf } from "../../api/books";
import type { Shelf } from "../../api/types";
import { cacheKeys } from "../../cache/keys";
import { invalidateCache } from "../../cache/invalidate";
import { useCachedQuery } from "../../composables/useCachedQuery";

const props = defineProps<{ bookId: number }>();

const {
  data: shelves,
  error: shelvesError,
  refresh: refreshShelves,
} = useCachedQuery<Shelf[]>(cacheKeys.shelves, getShelves);
const {
  data: bookShelves,
  error: bookShelvesError,
  refresh: refreshBookShelves,
} = useCachedQuery<Shelf[]>(
  computed(() => cacheKeys.shelvesForBook(props.bookId)),
  () => getBookShelves(props.bookId),
);
const updating = ref<string | null>(null);
const showShelfEditor = ref(false);
const openButton = ref<HTMLButtonElement | null>(null);
const closeButton = ref<HTMLButtonElement | null>(null);
const customShelves = computed(() => (shelves.value ?? []).filter((shelf) => shelf.ref.startsWith("custom:")));
const selected = computed(() => new Set((bookShelves.value ?? []).map((shelf) => shelf.ref)));
const selectedCustomShelves = computed(() =>
  (bookShelves.value ?? []).filter((shelf) => shelf.ref.startsWith("custom:")),
);

async function openShelfEditor() {
  showShelfEditor.value = true;
  await nextTick();
  closeButton.value?.focus();
}

async function closeShelfEditor() {
  if (!updating.value) {
    showShelfEditor.value = false;
    await nextTick();
    openButton.value?.focus();
  }
}

async function toggleShelf(shelf: Shelf) {
  if (updating.value) {
    return;
  }

  updating.value = shelf.ref;
  try {
    if (selected.value.has(shelf.ref)) {
      await removeBookFromShelf(shelf.ref, props.bookId);
    } else {
      await addBookToShelf(shelf.ref, props.bookId);
    }

    await invalidateCache.shelfChanged(props.bookId);
    await Promise.all([refreshShelves(), refreshBookShelves()]);
  } catch (error) {
    console.error("Failed to update shelves:", error);
    alert("Failed to update shelves");
  } finally {
    updating.value = null;
  }
}
</script>

<template>
  <section class="custom-shelves">
    <div class="section-header">
      <h2>Shelves</h2>
      <button ref="openButton" type="button" class="btn-small" @click="openShelfEditor">Update shelves</button>
    </div>

    <p v-if="bookShelvesError" class="error">Failed to load shelf memberships. Please try again.</p>
    <p v-else-if="!bookShelves" class="empty">Loading shelves...</p>
    <p v-else-if="!selectedCustomShelves.length" class="empty">Not in any shelves.</p>
    <ul v-else class="shelf-list" aria-label="Custom shelves">
      <li v-for="shelf in selectedCustomShelves" :key="shelf.ref">
        <RouterLink
          :to="{ name: 'custom-shelf', params: { id: shelf.ref.slice('custom:'.length) } }"
          class="shelf-link"
        >
          {{ shelf.display_name }}
        </RouterLink>
      </li>
    </ul>
  </section>

  <Teleport to="body">
    <div v-if="showShelfEditor" class="modal-overlay" @click.self="closeShelfEditor">
      <div
        class="modal"
        role="dialog"
        aria-modal="true"
        aria-labelledby="update-shelves-title"
        @keydown.esc="closeShelfEditor"
      >
        <div class="modal-header">
          <h3 id="update-shelves-title">Update shelves</h3>
          <button ref="closeButton" type="button" :disabled="updating !== null" @click="closeShelfEditor">Close</button>
        </div>
        <div class="modal-body">
          <p v-if="shelvesError" class="error">Failed to load shelves. Please try again.</p>
          <p v-else-if="bookShelvesError" class="error">Failed to load shelf memberships. Please try again.</p>
          <p v-else-if="!shelves || !bookShelves" class="empty">Loading shelves...</p>
          <p v-else-if="!customShelves.length" class="empty">No shelves yet.</p>
          <div v-else class="shelf-options" role="group" aria-label="Custom shelves">
            <label v-for="shelf in customShelves" :key="shelf.ref" class="shelf-option">
              <input
                type="checkbox"
                :checked="selected.has(shelf.ref)"
                :disabled="updating !== null"
                @change="toggleShelf(shelf)"
              />
              <span>{{ shelf.display_name }}</span>
            </label>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<style scoped>
.custom-shelves {
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-lg);
}
.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: var(--spacing-md);
  margin-bottom: var(--spacing-md);
}
h2 {
  margin: 0;
  font-size: 1.25rem;
}
.empty {
  margin: 0;
  color: var(--color-text-secondary);
}
.error {
  margin: 0;
  color: var(--color-danger);
}
.shelf-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding: 0;
  margin: 0;
  list-style: none;
}
.shelf-link {
  display: block;
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  color: var(--color-primary);
  text-decoration: none;
}
.shelf-link:hover {
  border-color: var(--color-primary);
}
.shelf-link:focus-visible {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.modal {
  display: flex;
  flex-direction: column;
  max-height: calc(100dvh - 2 * var(--spacing-sm));
  overflow: hidden;
}
.modal-header {
  flex-shrink: 0;
  gap: var(--spacing-sm);
}
.modal-body {
  min-height: 0;
  overflow-y: auto;
  overflow-x: hidden;
  overscroll-behavior: contain;
}
.shelf-options {
  display: grid;
  gap: var(--spacing-sm);
}
.shelf-option {
  display: flex;
  align-items: center;
  min-height: 48px;
  gap: var(--spacing-md);
  padding: var(--spacing-sm) var(--spacing-md);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  overflow-wrap: anywhere;
}
.shelf-option:hover {
  border-color: var(--color-primary);
}
.shelf-option:focus-within {
  outline: 2px solid var(--color-primary);
  outline-offset: 2px;
}
.shelf-option input {
  flex: none;
  width: 20px;
  height: 20px;
  margin: 0;
  accent-color: var(--color-primary);
}
@media (max-width: 600px) {
  .modal-overlay {
    align-items: center;
  }
  .modal-body {
    padding: var(--spacing-md);
  }
}
</style>
