import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { VitePWA } from "vite-plugin-pwa";
import { qrcode } from "vite-plugin-qrcode";

// The dev backend (`fastapi dev`) listens on 127.0.0.1 only. Proxying the API and the uploads
// through Vite keeps everything on that origin.
// Like this, also connecting from a mobile device works right away.
const backend = "http://127.0.0.1:8000";

const backendProxy = {
  "/api": backend,
  "/uploads": backend,
};

// https://vite.dev/config/
export default defineConfig({
  server: {
    host: true,
    proxy: backendProxy,
  },
  plugins: [
    qrcode(),
    vue(),
    VitePWA({
      registerType: "autoUpdate",
      injectRegister: "auto",
      includeAssets: ["logo.svg", "apple-touch-icon.png"],
      manifest: {
        name: "Books",
        short_name: "Books",
        start_url: "/",
        display: "standalone",
        background_color: "#ffffff",
        theme_color: "#ffffff",
        icons: [
          { src: "/pwa-192.png", sizes: "192x192", type: "image/png" },
          { src: "/pwa-512.png", sizes: "512x512", type: "image/png" },
        ],
      },
      workbox: {
        runtimeCaching: [
          {
            urlPattern: ({ request }) => request.destination === "image",
            handler: "StaleWhileRevalidate",
            options: {
              cacheName: "images",
            },
          },
        ],
      },
    }),
  ],
});
