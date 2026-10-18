<script setup lang="ts">
import { useId } from "vue";
import type { BookFormData } from "./bookForm";
import CoverEditField from "./cover/CoverEditField.vue";

defineProps<{
  disabled?: boolean;
  bookId?: number;
}>();

const formData = defineModel<BookFormData>({ required: true });
const id = useId();
</script>

<template>
  <fieldset :disabled="disabled" aria-label="Book details">
    <div class="form-group">
      <label :for="`${id}-title`">Title *</label>
      <input
        :id="`${id}-title`"
        v-model="formData.title"
        name="title"
        type="text"
        required
        maxlength="255"
        placeholder="Enter book title"
      />
    </div>

    <div class="form-group">
      <label :for="`${id}-author`">Author</label>
      <input
        :id="`${id}-author`"
        v-model="formData.author"
        name="author"
        type="text"
        maxlength="100"
        placeholder="Enter author name"
      />
    </div>

    <div class="form-row">
      <div class="form-group">
        <label :for="`${id}-isbn`">ISBN</label>
        <input
          :id="`${id}-isbn`"
          v-model="formData.isbn"
          name="isbn"
          type="text"
          maxlength="20"
          placeholder="Enter ISBN"
        />
      </div>
      <div class="form-group">
        <label :for="`${id}-page-count`">Page Count</label>
        <input
          :id="`${id}-page-count`"
          v-model="formData.page_count"
          name="page_count"
          type="number"
          min="0"
          step="1"
          placeholder="Number of pages"
        />
      </div>
    </div>

    <div class="form-group">
      <label :for="`${id}-published-date`">Published Date</label>
      <input :id="`${id}-published-date`" v-model="formData.published_date" name="published_date" type="date" />
    </div>

    <div class="form-group">
      <label :for="`${id}-description`">Description</label>
      <textarea
        :id="`${id}-description`"
        v-model="formData.description"
        name="description"
        rows="4"
        placeholder="Enter book description"
      ></textarea>
    </div>

    <CoverEditField
      v-model="formData.cover_image_url"
      :title="formData.title"
      :author="formData.author"
      :isbn="formData.isbn"
      :book-id="bookId"
      :disabled="disabled"
    />
  </fieldset>
</template>

<style scoped>
fieldset {
  border: 0;
  padding: 0;
  margin: 0;
  min-width: 0;
}
</style>
