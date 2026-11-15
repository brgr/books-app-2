import { persistQueryClient } from "@tanstack/query-persist-client-core";
import { VueQueryPlugin } from "@tanstack/vue-query";
import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import { CACHE_MAX_AGE, queryClient } from "./query/client";
import { persister } from "./query/persister";
import router from "./router";

const app = createApp(App);

app.use(router);
app.use(VueQueryPlugin, {
  queryClient,
  clientPersister: (client) => persistQueryClient({ queryClient: client, persister, maxAge: CACHE_MAX_AGE }),
});

app.mount("#app");

// The service worker used to cache every image here without a limit; it now uses the "covers" cache.
// Temporary: we can remove this once this code was executed on every device
if ("caches" in window) {
  void caches.delete("images");
}
