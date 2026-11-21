<script setup lang="ts">
defineProps<{
  thumbnailUrl: string | undefined;
  alt: string;
  title: string;
}>();

const emit = defineEmits<{
  select: [];
}>();
</script>

<template>
  <button type="button" class="cover-tile" :title="title" @click="emit('select')">
    <img :src="thumbnailUrl" :alt="alt" loading="lazy" />
    <span class="cover-caption">
      <slot />
    </span>
  </button>
</template>

<style scoped>
.cover-tile {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 6px;
  background-color: var(--color-bg-card);
  border: 1px solid var(--color-border);
  border-radius: var(--border-radius);
  cursor: pointer;
  text-align: left;
  transition:
    border-color 0.15s ease,
    transform 0.15s ease;
}

.cover-tile:hover {
  border-color: var(--color-primary);
  transform: translateY(-2px);
}

.cover-tile img {
  width: 100%;
  aspect-ratio: 2 / 3;
  object-fit: cover;
  border-radius: 4px;
  background-color: var(--color-bg);
}

.cover-caption {
  display: flex;
  flex-direction: column;
  gap: 2px;
  font-size: 12px;
}
</style>
