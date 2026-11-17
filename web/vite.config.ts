/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// La aplicación se sirve desde FastAPI en /app (web/dist). En desarrollo, Vite reenvía la API al backend local
// para mantener un único origen y evitar CORS; el GLB del auto lo sirve Vite desde public/models (/app/models).
export default defineConfig({
  base: "/app/",
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://127.0.0.1:8000",
      "/salud": "http://127.0.0.1:8000",
    },
  },
  build: { outDir: "dist", emptyOutDir: true, chunkSizeWarningLimit: 1500 },
  test: { environment: "jsdom", css: { include: [/ignis.css/] }, include: ["src/**/*.test.ts", "src/**/*.test.tsx"] },
});
