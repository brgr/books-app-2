import { VueQueryPlugin } from "@tanstack/vue-query";
import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import { queryClient } from "./query/client";
import { persistCache } from "./query/persister";
import router from "./router";

const app = createApp(App);

app.use(router);
app.use(VueQueryPlugin, {
  queryClient,
  clientPersister: persistCache,
});

app.mount("#app");

// The service worker used to cache every image here without a limit; it now uses the "covers" cache.
// Temporary: we can remove this once this code was executed on every device
if ("caches" in window) {
  void caches.delete("images");
}
