<script setup lang="ts">
import draggable from "vuedraggable";
import BookCard from "./BookCard/BookCard.vue";
import BookCoverTile from "./BookCoverTile.vue";
import type { Book } from "../../api/types";

/**
 * One shelf as rendered on the library page: an optional heading plus its books, laid out
 * either as a list of cards or as a draggable cover grid. Reordering is grid-only.
 * The parent persists the new order against the shelf this component shows.
 */
withDefaults(
  defineProps<{
    books: Book[];
    viewMode: "list" | "grid";
    /** Heading above the shelf. Omitted when the page shows a single, self-evident shelf. */
    title?: string | null;
    showProgress?: boolean;
    /** Whether covers can be dragged. Off while the shelf shows a subset the parent can't persist. */
    reorderable?: boolean;
  }>(),
  { title: null, showProgress: false, reorderable: false },
);

const dragOptions = {
  animation: 150,
  delay: 120,
  "delay-on-touch-only": true,
  "ghost-class": "grid-ghost",
  "drag-class": "grid-drag",
  "chosen-class": "grid-chosen",
};

defineEmits<{
  (e: "dragstart"): void;
  (e: "dragend", event: { newIndex?: number; oldIndex?: number }): void;
  (e: "select", bookId: number): void;
  (e: "menu", payload: { bookId: number; x: number; y: number }): void;
}>();
</script>

<template>
  <section class="shelf-section">
    <h2 v-if="title" class="shelf-section-title">{{ title }}</h2>

    <draggable
      v-if="viewMode === 'grid'"
      class="books-container books-grid"
      :list="books"
      item-key="id"
      :disabled="!reorderable"
      v-bind="dragOptions"
      @start="$emit('dragstart')"
      @end="$emit('dragend', $event)"
    >
      <template #item="{ element: book }">
        <BookCoverTile
          :book="book"
          :show-progress="showProgress"
          @click="$emit('select', $event)"
          @menu="$emit('menu', $event)"
        />
      </template>
    </draggable>

    <div v-else class="books-container books-list">
      <div v-for="book in books" :key="book.id">
        <BookCard :book="book" @menu="$emit('menu', $event)" />
      </div>
    </div>
  </section>
</template>

<style scoped>
.shelf-section-title {
  margin: 0 0 var(--spacing-sm);
  font-size: 0.95rem;
  font-weight: 700;
  color: var(--color-text);
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.books-container {
  overflow-x: clip;
  overflow-y: visible;
}

.books-list {
  display: flex;
  flex-direction: column;
}

.books-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 1.25rem;
  align-items: center;
  width: 100%;
  max-width: 100%;
  padding-top: 6px;
  padding-bottom: var(--spacing-sm);
  overflow-x: clip;
  overflow-y: visible;
}

/*noinspection CssUnusedSymbol*/
.books-grid :deep(.sortable-ghost .grid-cover),
.books-grid :deep(.sortable-ghost .grid-cover-placeholder),
.books-grid :deep(.sortable-chosen .grid-cover),
.books-grid :deep(.sortable-chosen .grid-cover-placeholder),
.books-grid :deep(.sortable-drag .grid-cover),
.books-grid :deep(.sortable-drag .grid-cover-placeholder) {
  transform: none;
  box-shadow: var(--shadow);
}

@media (max-width: 768px) {
  .books-grid {
    grid-template-columns: repeat(auto-fill, minmax(130px, 1fr));
    gap: 1.25rem;
  }
}

@media (max-width: 480px) {
  .books-grid {
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0.75rem;
  }
}

/* vuedraggable applies these classes at runtime to slot content during drag. */
/*noinspection CssUnusedSymbol*/
.grid-ghost {
  opacity: 0;
}

/*noinspection CssUnusedSymbol*/
.grid-drag,
.grid-chosen {
  opacity: 1 !important;
}
</style>
