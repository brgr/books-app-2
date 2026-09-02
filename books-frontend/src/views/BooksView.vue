<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import BookShelf from "../components/book/BookShelf.vue";
import BookSearchModal from "../components/modals/BookSearchModal.vue";
import BooksSearchHeader from "../components/ui/BooksSearchHeader.vue";
import LibraryNav from "../components/ui/LibraryNav.vue";
import NavigationBar from "../components/ui/NavigationBar.vue";
import { useAddBook } from "../composables/useAddBook";
import { provideLibraryPage } from "../composables/useLibraryPage";

const route = useRoute();
const router = useRouter();

const searchQuery = ref("");
// The shelf lives in the URL: /shelves/:shelf. Bare "/" is the shelf "to-read".
const shelfFilter = computed<"to-read" | "finished" | "abandoned">(() => {
  if (route.params.shelf === "finished") return "finished";
  if (route.params.shelf === "abandoned") return "abandoned";
  return "to-read";
});

const navSurface = computed<"to-read" | "finished" | "shelves">(() =>
  shelfFilter.value === "abandoned" ? "shelves" : shelfFilter.value,
);

function goToShelf(shelf: "to-read" | "finished" | "shelves") {
  router.push(shelf === "shelves" ? { name: "custom-shelves" } : { name: "shelf", params: { shelf } });
}

const { allShelvesEmpty, refreshShelves } = provideLibraryPage({ searchQuery });

const { showSearchModal, openSearch, closeSearch, selectBook } = useAddBook(refreshShelves);
</script>

<template>
  <div class="books-view">
    <NavigationBar @add-book="openSearch">
      <template #nav>
        <LibraryNav :model-value="navSurface" @update:model-value="goToShelf" />
      </template>
    </NavigationBar>

    <div class="container">
      <BooksSearchHeader v-model:search-query="searchQuery" />

      <div v-if="allShelvesEmpty" class="empty-state">
        <p v-if="searchQuery">No books match your search.</p>
        <p v-else-if="shelfFilter === 'finished'">No finished books yet.</p>
        <p v-else>No books yet. Add your first book to get started!</p>
      </div>

      <div class="shelves">
        <template v-if="shelfFilter === 'to-read'">
          <!-- Books in progress load as a single page of up to 100: more than a user realistically
               reads at once. Worth revisiting if that ever stops holding. -->
          <BookShelf shelf="reading:started" title="Reading now" show-progress :page-size="100" />
          <BookShelf shelf="reading:paused" title="Paused Books" :page-size="100" />
          <BookShelf shelf="reading:want_to_read" title="Want to read" paginated />
        </template>
        <BookShelf v-else-if="shelfFilter === 'finished'" shelf="reading:finished" paginated />
        <BookShelf v-else shelf="reading:abandoned" title="Abandoned Books" paginated />
      </div>
    </div>

    <BookSearchModal v-if="showSearchModal" @close="closeSearch" @select="selectBook" />
  </div>
</template>

<style scoped>
.books-view {
  min-height: 100svh;
  padding-bottom: 112px;
  box-sizing: border-box;
  background-color: var(--color-bg);
}

.empty-state {
  text-align: center;
  padding: var(--spacing-xl);
  color: var(--color-text-secondary);
}

.shelves {
  margin-top: var(--spacing-lg);
}

.shelves > * + * {
  margin-top: var(--spacing-lg);
}

/* Desktop: LibraryNav is inline tabs, not a fixed bar: drop the reserved space. */
@media (min-width: 769px) {
  .books-view {
    padding-bottom: var(--spacing-xl);
  }
}
</style>
