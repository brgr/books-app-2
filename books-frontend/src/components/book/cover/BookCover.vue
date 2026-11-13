<script setup lang="ts">
import { computed, ref } from "vue";
import { getMediaUrl } from "../../../api/client";

/**
 * A book's large cover. Shows the (usually already cached) thumbnail until the full cover is ready to paint.
 */
const props = defineProps<{
  title: string;
  coverUrl: string | null;
  thumbnailUrl: string | null;
}>();

const loadedCover = ref<string>();
const largeCoverUrl = computed(() => getMediaUrl(props.coverUrl));
const smallCoverUrl = computed(() => getMediaUrl(props.thumbnailUrl));
const hasThumbnail = computed(() =>
  Boolean(smallCoverUrl.value && largeCoverUrl.value && smallCoverUrl.value !== largeCoverUrl.value),
);
// Comparing against the current URL means a new cover starts out behind its thumbnail again
const showThumbnail = computed(() => hasThumbnail.value && loadedCover.value !== largeCoverUrl.value);

async function revealCover(event: Event) {
  const image = event.currentTarget as HTMLImageElement;
  const url = image.getAttribute("src");
  try {
    // Loading finishes before the browser necessarily has pixels ready to paint
    await image.decode?.();
  } catch {
    return; // Keep the thumbnail if decoding fails
  }
  if (url === largeCoverUrl.value) {
    loadedCover.value = url;
  }
}
</script>

<template>
  <div v-if="largeCoverUrl || smallCoverUrl" class="book-cover-stack">
    <!-- Retain the thumbnail's layout box: rounded thumbnail dimensions can differ from the full cover -->
    <img
      v-if="hasThumbnail"
      :src="smallCoverUrl"
      :alt="showThumbnail ? title : ''"
      :aria-hidden="!showThumbnail ? true : undefined"
      class="book-cover-large"
      :class="{ 'book-cover-loading': !showThumbnail }"
    />
    <img
      :key="largeCoverUrl || smallCoverUrl"
      :src="largeCoverUrl || smallCoverUrl"
      :alt="showThumbnail ? '' : title"
      :aria-hidden="showThumbnail ? true : undefined"
      class="book-cover-large"
      :class="{ 'book-cover-overlay': hasThumbnail, 'book-cover-loading': showThumbnail }"
      @load="revealCover"
    />
  </div>
  <div v-else class="book-cover-large book-cover-placeholder">No Cover</div>
</template>

<style scoped>
.book-cover-stack {
  position: relative;
  width: min(240px, 100%);
}

.book-cover-loading {
  visibility: hidden;
}

.book-cover-large {
  width: min(240px, 100%);
  max-width: 100%;
  height: auto;
  border-radius: var(--border-radius);
  box-shadow: var(--shadow);
  display: block;
  user-select: none;
  -webkit-user-select: none;
  -webkit-touch-callout: none;
  touch-action: manipulation;
}

.book-cover-large.book-cover-overlay {
  position: absolute;
  inset: 0;
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.book-cover-placeholder {
  aspect-ratio: 2 / 3;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  color: var(--color-text-secondary);
  font-size: 14px;
  text-align: center;
}

@media (max-width: 768px) {
  .book-cover-large,
  .book-cover-stack {
    width: min(200px, 100%);
    height: auto;
  }
}
</style>
