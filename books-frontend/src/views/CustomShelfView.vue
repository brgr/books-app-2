<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { deleteShelf, getShelves, renameShelf } from "../api/books";
import { parseShelfRef, type Shelf, type ShelfRef } from "../api/types";
import BookShelf from "../components/book/BookShelf.vue";
import CustomShelfEditModal from "../components/modals/CustomShelfEditModal.vue";
import BooksSearchHeader from "../components/ui/BooksSearchHeader.vue";
import NavigationBar from "../components/ui/NavigationBar.vue";
import { cacheKeys } from "../cache/keys";
import { cacheDel } from "../cache/store";
import { provideLibraryPage } from "../composables/useLibraryPage";
import { useCachedQuery } from "../composables/useCachedQuery";

const route = useRoute();
const router = useRouter();
const searchQuery = ref("");
const shelfRef = computed<ShelfRef>(() => {
  const id = route.params.id;
  if (typeof id !== "string") throw new Error("Invalid custom shelf route");
  return parseShelfRef(`custom:${id}`);
});

const { data: shelves, error: shelvesError, refresh } = useCachedQuery<Shelf[]>(cacheKeys.shelves, getShelves);
const shelf = computed(() => (shelves.value ?? []).find((item) => item.ref === shelfRef.value));
const { allShelvesEmpty } = provideLibraryPage({ searchQuery });
const showEditShelf = ref(false);
const saving = ref(false);
const actionError = ref("");

function openEditShelf() {
  actionError.value = "";
  showEditShelf.value = true;
}

function closeEditShelf() {
  showEditShelf.value = false;
  actionError.value = "";
}

function clearActionError() {
  actionError.value = "";
}

async function saveRename(name: string) {
  if (saving.value) return;

  saving.value = true;
  actionError.value = "";
  try {
    await renameShelf(shelfRef.value, name);
    await refresh();
    closeEditShelf();
  } catch (error) {
    console.error("Failed to rename shelf:", error);
    actionError.value = error instanceof Error ? error.message : "Failed to rename shelf.";
  } finally {
    saving.value = false;
  }
}

async function confirmDeleteShelf() {
  if (saving.value) return;

  saving.value = true;
  actionError.value = "";
  try {
    await deleteShelf(shelfRef.value);

    // Invalidate the shelves cache so that the deleted shelf is removed from the list
    await cacheDel(cacheKeys.shelves());

    // After deleting the shelf, remove that shelf from the navigation and go back to the custom shelves page instead
    await router.replace({ name: "custom-shelves" });
  } catch (error) {
    console.error("Failed to delete shelf:", error);
    actionError.value = error instanceof Error ? error.message : "Failed to delete shelf.";
  } finally {
    saving.value = false;
  }
}
</script>

<template>
  <div class="custom-shelf-page">
    <NavigationBar />

    <div class="container">
      <BooksSearchHeader v-model:search-query="searchQuery" />

      <div v-if="shelvesError" class="error-state">
        Failed to load this shelf. Please try again.
        <button type="button" class="btn-small" @click="refresh">Retry</button>
      </div>
      <div v-else-if="!shelves" class="loading">Loading shelf...</div>
      <div v-else-if="!shelf" class="empty-state">This shelf no longer exists.</div>
      <template v-else>
        <header class="shelf-heading">
          <h1>{{ shelf.display_name }}</h1>
          <button type="button" class="btn-small" @click="openEditShelf">Edit shelf</button>
        </header>

        <p v-if="allShelvesEmpty" class="empty-state">No books on this shelf yet.</p>
        <BookShelf :shelf="shelfRef" :title="null" paginated can-remove-from-shelf />
      </template>
    </div>

    <CustomShelfEditModal
      v-if="showEditShelf"
      :shelf-name="shelf?.display_name ?? ''"
      :saving="saving"
      :error="actionError"
      @close="closeEditShelf"
      @rename="saveRename"
      @request-delete="clearActionError"
      @delete="confirmDeleteShelf"
    />
  </div>
</template>

<style scoped>
.custom-shelf-page {
  min-height: 100svh;
  padding-bottom: 112px;
  background: var(--color-bg);
}
.shelf-heading {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: var(--spacing-lg) 0;
  gap: var(--spacing-md);
}
h1 {
  margin: 0;
  font-size: 1.5rem;
}
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}
.error-state {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: var(--spacing-md);
  padding: var(--spacing-xl);
  color: var(--color-danger);
}
@media (min-width: 769px) {
  .custom-shelf-page {
    padding-bottom: var(--spacing-xl);
  }
}
</style>
