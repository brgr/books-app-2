<script setup lang="ts">
import { useRouter } from "vue-router";
import BookNotesAndRating from "../components/book/BookNotesAndRating.vue";
import BookReadingStatus from "../components/book/BookReadingStatus.vue";
import BackToShelfLink from "../components/navigation/BackToShelfLink.vue";
import NavigationBar from "../components/navigation/NavigationBar.vue";
import CollapsibleText from "../components/ui/CollapsibleText.vue";
import BookMetadata from "../components/book/BookMetadata.vue";
import EventTimeline from "../components/book/EventTimeline.vue";
import BookCustomShelves from "../components/book/BookCustomShelves.vue";
import BookCover from "../components/book/cover/BookCover.vue";
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

            <BookReadingStatus
              :user-book="book.user_book"
              :page-count="book.page_count"
              :saving-shelf="savingShelf"
              :saving-progress="savingProgress"
              @change="changeShelf"
              @update-progress="saveProgress"
            />
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
  overflow: hidden;
}

.book-header {
  display: grid;
  grid-template-columns: minmax(220px, 260px) minmax(0, 1fr);
  column-gap: var(--spacing-xl);
  padding: var(--spacing-xl);
  align-items: flex-start;
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
}

.book-actions button {
  flex: 0 0 auto;
  min-width: 140px;
  max-width: 220px;
}

.book-body {
  padding: var(--spacing-xl);
  overflow-x: hidden;
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
    min-height: 100%;
  }

  .book-header {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    padding: var(--spacing-lg) 0;
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

  .book-actions {
    flex-direction: column;
  }

  .book-actions button {
    width: 100%;
  }

  .book-body {
    padding: var(--spacing-lg) 0;
  }
}
</style>
