<script setup lang="ts">
import { computed } from "vue";
import { useRouter } from "vue-router";
import BookNotesAndRating from "../components/book/BookNotesAndRating.vue";
import BookShelfButton from "../components/book/BookShelfButton/BookShelfButton.vue";
import BookReadingCard from "../components/book/BookReadingCard/BookReadingCard.vue";
import type { ReadingProgress } from "../components/book/BookReadingCard/types";
import BackToShelfLink from "../components/navigation/BackToShelfLink.vue";
import NavigationBar from "../components/navigation/NavigationBar.vue";
import CollapsibleText from "../components/ui/CollapsibleText.vue";
import BookMetadata from "../components/book/BookMetadata.vue";
import EventTimeline from "../components/book/EventTimeline.vue";
import BookCustomShelves from "../components/book/BookCustomShelves.vue";
import BookCover from "../components/book/cover/BookCover.vue";
import { ReadingShelf } from "../api/types";
import { formatReadingDate } from "../utils/date";
import { useRouteBookId } from "../composables/useBook";
import { useBookDetail } from "../composables/useBookDetail";

const router = useRouter();
const bookId = useRouteBookId();

const {
  book,
  events,
  error,
  savingShelf,
  savingReview,
  savingProgress,
  reviewError,
  changeShelf,
  saveProgress,
  saveReview,
} = useBookDetail(bookId);

const currentProgress = computed<ReadingProgress>(() => {
  const startingProgress: ReadingProgress = { unit: book.value?.page_count != null ? "page" : "percent", value: 0 };
  return book.value?.user_book.progress ?? startingProgress;
});

const canUpdateProgress = computed(() => book.value?.user_book.shelf === ReadingShelf.STARTED);

function handleEdit() {
  if (!book.value) {
    return;
  }

  router.push({ name: "book-edit", params: { id: book.value.id } });
}
</script>

<template>
  <div class="book-detail-page">
    <NavigationBar />

    <div class="container">
      <BackToShelfLink />
      <div v-if="!book && !error" class="loading">Loading book...</div>

      <div v-else-if="error && !book" class="error">
        {{ error }}
      </div>

      <div v-else-if="book" class="book-detail">
        <div class="book-header">
          <div class="book-cover-section">
            <BookCover
              :title="book.title"
              :cover-url="book.cover_image_url"
              :thumbnail-url="book.cover_thumbnail_url"
            />
          </div>

          <div class="book-info">
            <h1>{{ book.title }}</h1>
            <p v-if="book.author" class="book-author">by {{ book.author }}</p>

            <div class="book-shelf-section">
              <BookShelfButton
                v-if="!canUpdateProgress"
                :shelf="book.user_book.shelf"
                :updating="savingShelf"
                @change="changeShelf"
              />

              <BookReadingCard
                v-else
                :shelf="book.user_book.shelf"
                :updating="savingShelf"
                :progress="currentProgress"
                :page-count="book.page_count"
                :started-at="book.user_book.started_at"
                :finished-at="book.user_book.finished_at"
                :progress-saving="savingProgress"
                @change="changeShelf"
                @update-progress="saveProgress"
              />
            </div>

            <div v-if="!canUpdateProgress" class="book-dates">
              <div v-if="book.user_book.started_at" class="date-item">
                <strong>Started:</strong> {{ formatReadingDate(book.user_book.started_at) }}
              </div>
              <div v-if="book.user_book.finished_at" class="date-item">
                <strong>Finished:</strong> {{ formatReadingDate(book.user_book.finished_at) }}
              </div>
            </div>
          </div>
        </div>

        <div class="book-body">
          <div v-if="book.description" class="book-description">
            <h2>Description</h2>
            <CollapsibleText :text="book.description" />
          </div>

          <BookNotesAndRating
            :key="book.id"
            :notes="book.user_book.notes ?? ''"
            :rating="book.user_book.rating"
            :saving="savingReview"
            :error="reviewError"
            @save="saveReview"
          />

          <BookCustomShelves :book-id="book.id" />

          <BookMetadata :book="book" />

          <EventTimeline :events="events ?? []" />

          <div class="book-actions">
            <button class="btn-primary" @click="handleEdit">Edit Book</button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.book-detail-page {
  min-height: 100vh;
  background-color: var(--color-bg);
}

.book-detail {
  background: transparent;
  border-radius: var(--border-radius);
  box-shadow: none;
  overflow: hidden;
  max-width: 100%;
}

.book-header {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  column-gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  background: transparent;
  align-items: flex-start;
  width: 100%;
  max-width: 100%;
}

.book-cover-section {
  flex-shrink: 0;
  max-width: 100%;
}

.book-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
  width: 100%;
}

.book-info h1 {
  margin: 0 0 var(--spacing-sm) 0;
  font-size: 2rem;
  line-height: 1.2;
  word-break: break-word;
}

.book-author {
  margin: 0 0 var(--spacing-lg) 0;
  color: var(--color-text-secondary);
  font-size: 1.125rem;
  word-break: break-word;
}

.book-actions {
  display: flex;
  gap: var(--spacing-md);
  margin-top: var(--spacing-xl);
  margin-bottom: var(--spacing-xl);
  flex-wrap: wrap;
  justify-content: flex-start;
}

.book-actions button {
  flex: 0 0 auto;
  min-width: 140px;
  max-width: 220px;
  width: auto;
}

.book-shelf-section {
  margin-bottom: var(--spacing-lg);
  padding: 0;
  background-color: transparent;
  border: none;
  display: flex;
  flex-direction: column;
  gap: var(--spacing-md);
}

.book-dates {
  display: flex;
  flex-direction: column;
  gap: var(--spacing-xs);
}

.date-item {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.date-item strong {
  color: var(--color-text);
}

.book-body {
  padding: var(--spacing-xl);
  overflow-x: hidden;
  background: transparent;
}

.book-description {
  margin-bottom: var(--spacing-xl);
}

.book-description h2 {
  margin: 0 0 var(--spacing-md) 0;
  font-size: 1.25rem;
}

@media (max-width: 768px) {
  .book-detail-page {
    border-radius: 0;
    min-height: 100%;
  }

  .book-detail {
    border: none;
    border-radius: 0;
    box-shadow: none;
    background: transparent;
  }

  .book-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--spacing-lg) 0;
    flex-wrap: wrap;
  }

  .book-cover-section {
    display: flex;
    justify-content: center;
    width: 100%;
    margin-bottom: var(--spacing-lg);
  }

  .book-info h1 {
    font-size: 1.5rem;
  }

  .book-info {
    width: 100%;
  }

  .book-actions {
    flex-direction: column;
  }

  .book-actions button {
    width: 100%;
    flex: 0 0 auto;
  }

  .book-shelf-section {
    align-items: center;
  }

  .book-shelf-section select {
    max-width: 100%;
  }

  .book-body {
    padding: var(--spacing-lg) 0;
  }
}
</style>
