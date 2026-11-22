<script setup lang="ts">
import { computed } from "vue";
import { type Book, ReadingShelf } from "../../../api/types";
import { getMediaUrl } from "../../../api/client";
import { isPlainLeftClick } from "../../../utils/click";

const props = withDefaults(
  defineProps<{
    book: Book;
    href: string;
    showProgress?: boolean;
  }>(),
  { showProgress: false },
);

const emit = defineEmits<{
  (e: "click", bookId: number): void;
  (e: "menu", payload: { bookId: number; x: number; y: number }): void;
}>();

// Open the menu here only on a right-click: a long press on touch belongs to the shelf, which also starts the drag
// from it. Android fires `contextmenu` on a long press too; `touchActive` tells the two apart
let touchActive = false;

function setTouchActive(active: boolean) {
  touchActive = active;
}

function onContextMenu(e: MouseEvent) {
  e.preventDefault();
  if (touchActive) {
    return;
  }

  emit("menu", { bookId: props.book.id, x: e.clientX, y: e.clientY });
}

function onClick(event: MouseEvent) {
  // Ordinary clicks are handled by ourselves; for clicks with special keys, keep the browser's usual (link) behavior
  if (!isPlainLeftClick(event)) {
    return;
  }

  event.preventDefault();
  emit("click", props.book.id);
}

const coverUrl = computed(() => getMediaUrl(props.book.cover_thumbnail_url || props.book.cover_image_url));

// Null when there is nothing to show: no progress yet, or pages without a known page count.
const progressPercent = computed<number | null>(() => {
  const progress = props.book.progress;
  const pageCount = props.book.page_count;
  let percent: number;

  if (progress?.unit === "percent") {
    percent = progress.value;
  } else if (progress && pageCount) {
    percent = (progress.value / pageCount) * 100;
  } else {
    return null;
  }

  return Math.min(100, Math.max(0, Math.round(percent)));
});

const showBadge = computed(
  () => props.showProgress && props.book.shelf === ReadingShelf.STARTED && progressPercent.value !== null,
);
</script>

<template>
  <div class="grid-item">
    <a
      :href="href"
      draggable="false"
      class="grid-cover-link"
      @click="onClick"
      @contextmenu="onContextMenu"
      @touchstart.passive="setTouchActive(true)"
      @touchend.passive="setTouchActive(false)"
      @touchcancel.passive="setTouchActive(false)"
    >
      <span v-if="showBadge" class="grid-progress-badge"> {{ progressPercent }}% </span>
      <span
        v-if="book.rating !== null"
        class="grid-rating-badge"
        :aria-label="`Your rating: ${book.rating} out of 5 stars`"
      >
        <span aria-hidden="true">★ {{ book.rating }}</span>
      </span>
      <img
        v-if="coverUrl"
        :src="coverUrl"
        :alt="book.title"
        :title="book.author ? book.title + ' by ' + book.author : book.title"
        class="grid-cover"
        loading="lazy"
        draggable="false"
      />
      <div v-else class="grid-cover-placeholder" :title="book.author ? book.title + ' by ' + book.author : book.title">
        <div class="grid-no-cover-text">{{ book.title }}</div>
      </div>
    </a>
  </div>
</template>

<style scoped>
.grid-item {
  display: flex;
  flex-direction: column;
  justify-content: flex-end;
  min-width: 0;
  width: 100%;
  max-width: 100%;
  overflow: visible;
}

.grid-cover-link {
  padding: 0;
  border: none;
  background: transparent;
  text-decoration: none;
  display: block;
  cursor: grab;
  width: 100%;
  text-align: left;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
  position: relative;
  border-radius: 6px;
  transition: transform 0.2s ease;
}

/* Shade the edges inward and let the top edge catch a little light: the cover looks like a softly padded board */
.grid-cover-link::after {
  content: "";
  position: absolute;
  inset: 0;
  z-index: 1;
  border-radius: inherit;
  pointer-events: none;
  box-shadow:
    inset 0 0 10px rgba(0, 0, 0, 0.11),
    inset 0 1px 0 rgba(255, 255, 255, 0.22);
}

.grid-cover {
  width: 100%;
  max-width: 100%;
  height: auto;
  border-radius: inherit;
  cursor: pointer;
  transition: box-shadow 0.2s ease;
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.12),
    0 4px 10px rgba(0, 0, 0, 0.1);
  display: block;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  /* Block iOS's native image drag-and-drop, which fires pointercancel and tears down the
     SortableJS drag session when the long-press menu appears. */
  -webkit-user-drag: none;
  touch-action: manipulation;
}

.grid-cover-placeholder {
  width: 100%;
  max-width: 100%;
  aspect-ratio: 2/3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: inherit;
  cursor: pointer;
  transition: box-shadow 0.2s ease;
  box-shadow:
    0 1px 2px rgba(0, 0, 0, 0.12),
    0 4px 10px rgba(0, 0, 0, 0.1);
  padding: var(--spacing-md);
  /* Keep the 2:3 ratio even for long titles. Without this the flex box's automatic min-height lets the
   text push the placeholder taller. */
  overflow: hidden;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.grid-no-cover-text {
  text-align: center;
  color: var(--color-text);
  font-size: 14px;
  font-weight: 500;
  word-break: break-word;
  line-height: 1.4;
  /* Truncate very long titles with an ellipsis instead of overflowing the cover. */
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 8;
  line-clamp: 8;
  overflow: hidden;
  max-height: 100%;
}

.grid-rating-badge,
.grid-progress-badge {
  position: absolute;
  right: 6px;
  bottom: 6px;
  z-index: 2;
  background: rgba(20, 24, 31, 0.85);
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  padding: 4px 7px;
  border-radius: 999px;
  letter-spacing: 0.02em;
  box-shadow: 0 4px 10px rgba(0, 0, 0, 0.25);
  pointer-events: none;
  transition: box-shadow 0.2s ease;
}

.grid-rating-badge {
  bottom: auto;
  top: 6px;
}

/* Lift a book on hover only with a mouse or trackpad. Touch screens keep :hover on whatever was last touched, which
   would leave a tapped or dragged book lifted */
@media (hover: hover) {
  .grid-cover-link:hover {
    transform: translateY(-4px);
  }

  .grid-cover-link:hover .grid-cover,
  .grid-cover-link:hover .grid-cover-placeholder {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.2);
  }

  .grid-cover-link:hover .grid-progress-badge {
    box-shadow: 0 8px 16px rgba(0, 0, 0, 0.25);
  }
}
</style>
