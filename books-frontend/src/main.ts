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
