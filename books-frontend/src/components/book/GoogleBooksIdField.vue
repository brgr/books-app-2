<script setup lang="ts">
import { useId } from "vue";
import GoogleBooksIdPicker from "./GoogleBooksIdPicker.vue";

defineProps<{
  title: string;
  author: string;
  isbn: string;
}>();

const googleBooksId = defineModel<string>({ required: true });
const id = useId();
</script>

<template>
  <div class="form-group">
    <label :for="id">Google Books ID</label>
    <input
      :id="id"
      v-model="googleBooksId"
      name="google_books_id"
      type="text"
      maxlength="128"
      placeholder="Enter Google Books ID"
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
