import { VueQueryPlugin } from "@tanstack/vue-query";
import { createApp } from "vue";
import "./style.css";
import App from "./App.vue";
import { queryClient } from "./query/client";
import router from "./router";

const app = createApp(App);

app.use(router);
app.use(VueQueryPlugin, { queryClient });

app.mount("#app");
