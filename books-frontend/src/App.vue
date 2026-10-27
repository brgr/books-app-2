<script setup lang="ts">
import { libraryPageKey } from "./router/libraryNavigation";
</script>

<template>
  <RouterView v-slot="{ Component, route }">
    <KeepAlive v-if="route.name !== 'login'" include="BooksView,CustomShelfView,CustomShelvesView">
      <component :is="Component" :key="libraryPageKey(route) ?? route.path" />
    </KeepAlive>
    <component :is="Component" v-else />
  </RouterView>
</template>
