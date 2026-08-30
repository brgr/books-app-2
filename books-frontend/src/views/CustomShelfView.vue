<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { getShelves } from "../api/books";
import { parseShelfRef, type Shelf, type ShelfRef } from "../api/types";
import BookShelf from "../components/book/BookShelf.vue";
import BookSearchModal from "../components/modals/BookSearchModal.vue";
import BooksSearchHeader from "../components/ui/BooksSearchHeader.vue";
import LibraryNav from "../components/ui/LibraryNav.vue";
import NavigationBar from "../components/ui/NavigationBar.vue";
import { cacheKeys } from "../cache/keys";
import { useAddBook } from "../composables/useAddBook";
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

const { data: shelves } = useCachedQuery<Shelf[]>(cacheKeys.shelves, getShelves);
const shelf = computed(() => (shelves.value ?? []).find((item) => item.ref === shelfRef.value));
const { allShelvesEmpty, refreshShelves } = provideLibraryPage({ searchQuery });
const { showSearchModal, openSearch, closeSearch, selectBook } = useAddBook(refreshShelves);

function goTo(surface: "to-read" | "finished" | "shelves") {
  router.push(surface === "shelves" ? { name: "custom-shelves" } : { name: "shelf", params: { shelf: surface } });
}
</script>

<template>
  <div class="custom-shelf-page">
    <NavigationBar @add-book="openSearch">
      <template #nav><LibraryNav model-value="shelves" @update:model-value="goTo" /></template>
    </NavigationBar>

    <div class="container">
      <BooksSearchHeader v-model:search-query="searchQuery" />

      <h1>{{ shelf?.display_name ?? "Shelf" }}</h1>
      <p v-if="allShelvesEmpty" class="empty-state">No books on this shelf yet.</p>
      <BookShelf :shelf="shelfRef" :title="null" paginated />
    </div>
    <BookSearchModal v-if="showSearchModal" @close="closeSearch" @select="selectBook" />
  </div>
</template>

<style scoped>
.custom-shelf-page {
  min-height: 100svh;
  padding-bottom: 112px;
  background: var(--color-bg);
}
h1 {
  margin: var(--spacing-lg) 0;
  font-size: 1.5rem;
}
.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}
@media (min-width: 769px) {
  .custom-shelf-page {
    padding-bottom: var(--spacing-xl);
  }
}
</style>
