<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";
import { libraryOrigin } from "../../router/libraryNavigation";
import { isPlainLeftClick } from "../../utils/click";

const router = useRouter();
const route = useRoute();
const shelf = computed(() => libraryOrigin(router, route.query?.from));

function returnToShelf(event: MouseEvent, navigate: (event: MouseEvent) => unknown) {
  // Use browser history when the shelf is immediately behind us, so Forward reopens the book
  if (!event.defaultPrevented && isPlainLeftClick(event) && router.options.history.state.back === shelf.value) {
    event.preventDefault();
    router.back();
    return;
  }

  void navigate(event);
}
</script>

<template>
  <RouterLink v-slot="{ href, navigate }" :to="shelf" custom>
    <a :href="href" class="back-to-shelf" @click="returnToShelf($event, navigate)">
      <span aria-hidden="true">←</span> Back to shelf
    </a>
  </RouterLink>
</template>

<style scoped>
.back-to-shelf {
  display: inline-flex;
  align-items: center;
  gap: var(--spacing-sm);
  min-height: 44px;
  margin-bottom: var(--spacing-md);
  color: var(--color-primary);
  text-decoration: none;
}

.back-to-shelf:hover {
  text-decoration: underline;
}
</style>
