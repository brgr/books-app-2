<script setup lang="ts">
import { computed, ref } from "vue";
import { addBookToShelf, getBookShelves, getShelves, removeBookFromShelf } from "../../api/books";
import type { Shelf } from "../../api/types";
import { cacheKeys } from "../../cache/keys";
import { invalidateCache } from "../../cache/invalidate";
import { useCachedQuery } from "../../composables/useCachedQuery";

const props = defineProps<{ bookId: number }>();

const { data: shelves, refresh: refreshShelves } = useCachedQuery<Shelf[]>(cacheKeys.shelves, getShelves);
const { data: bookShelves, refresh: refreshBookShelves } = useCachedQuery<Shelf[]>(
  computed(() => cacheKeys.shelvesForBook(props.bookId)),
  () => getBookShelves(props.bookId),
);
const updating = ref<string | null>(null);
const showShelfEditor = ref(false);
const customShelves = computed(() => (shelves.value ?? []).filter((shelf) => shelf.ref.startsWith("custom:")));
const selected = computed(() => new Set((bookShelves.value ?? []).map((shelf) => shelf.ref)));
const selectedCustomShelves = computed(() =>
  (bookShelves.value ?? []).filter((shelf) => shelf.ref.startsWith("custom:")),
);

function closeShelfEditor() {
  if (!updating.value) showShelfEditor.value = false;
}

async function toggleShelf(shelf: Shelf) {
  if (updating.value) return;
  updating.value = shelf.ref;
  try {
    if (selected.value.has(shelf.ref)) await removeBookFromShelf(shelf.ref, props.bookId);
    else await addBookToShelf(shelf.ref, props.bookId);
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
      <button type="button" class="btn-small" @click="showShelfEditor = true">Update shelves</button>
    </div>

    <p v-if="!selectedCustomShelves.length" class="empty">Not in any shelves.</p>
    <ul v-else class="shelf-list" aria-label="Custom shelves">
      <li v-for="shelf in selectedCustomShelves" :key="shelf.ref">{{ shelf.display_name }}</li>
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
          <button type="button" class="btn-small" :disabled="updating !== null" @click="closeShelfEditor">Close</button>
        </div>
        <div class="modal-body">
          <p v-if="!customShelves.length" class="empty">No shelves yet.</p>
          <div v-else class="shelf-options">
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
.shelf-list {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm);
  padding: 0;
  margin: 0;
  list-style: none;
}
.shelf-list li {
  padding: var(--spacing-xs) var(--spacing-sm);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
}
.shelf-options {
  display: flex;
  flex-wrap: wrap;
  gap: var(--spacing-sm) var(--spacing-lg);
}
.shelf-option {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  cursor: pointer;
}
.shelf-option input {
  accent-color: var(--color-primary);
}
</style>
