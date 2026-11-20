<script setup lang="ts">
import { libraryPageKey } from "./router/libraryNavigation";
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <!-- Each page gets its own scroller: iOS can stop scrolling a reused one after a swipe back -->
    <div :key="libraryPageKey(route) ?? route.path" class="page-scroller">
      <component :is="Component" />
    </div>
  </RouterView>
</template>
