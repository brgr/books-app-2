<script setup lang="ts">
import { computed, useId } from "vue";
import { googleBooksIdFromUrl } from "./googleBooksId";
import GoogleBooksIdPicker from "./GoogleBooksIdPicker.vue";

defineProps<{
  title: string;
  author: string;
  isbn: string;
}>();

const googleBooksId = defineModel<string>({ required: true });
const id = useId();

// Keep only the id when a Google Books link is pasted into the field
const inputValue = computed({
  get: () => googleBooksId.value,
  set: (value: string) => {
    googleBooksId.value = googleBooksIdFromUrl(value) ?? value;
  },
});
</script>

<template>
  <div class="form-group">
    <label :for="id">Google Books ID</label>
    <input
      :id="id"
      v-model="inputValue"
      name="google_books_id"
      type="text"
      placeholder="Enter Google Books ID or paste a Google Books link"
    />
    <GoogleBooksIdPicker
      v-if="!googleBooksId.trim()"
      :title="title"
      :author="author"
      :isbn="isbn"
      @select="googleBooksId = $event"
    />
  </div>
</template>
