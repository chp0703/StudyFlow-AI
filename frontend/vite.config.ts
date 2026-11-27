import { defineConfig } from "vite"

import react from "@vitejs/plugin-react"

import tailwindcss from "@tailwindcss/vite"

export default defineConfig({
  plugins: [react(), tailwindcss()],

  // Keep optimized dependencies local to this checkout, even with a shared node_modules.
  cacheDir: ".vite",

  server: { port: Number(process.env.PORT) || 5173 },

  preview: { port: Number(process.env.PORT) || 4173 },
})
