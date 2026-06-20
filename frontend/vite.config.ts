import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        secure: false,
        timeout: 20000,
        proxyTimeout: 120000, // keep long for SSE streaming (/api/query)
      },
      "/ws": {
        target: "ws://127.0.0.1:8000", // 👈 Changed from localhost to 127.0.0.1
        ws: true,
      },
    },
  },
});
