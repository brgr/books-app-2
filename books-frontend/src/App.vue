<script setup lang="ts">
import { libraryPageKey } from "./router/libraryNavigation";
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <component :is="Component" :key="libraryPageKey(route) ?? route.path" />
  </RouterView>
</template>
