import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { defineConfig } from 'vite'
import { fileURLToPath } from 'node:url'

const frontendModules = fileURLToPath(new URL('./node_modules', import.meta.url))

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: {
    proxy: {
      '/api/v1': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  resolve: {
    alias: [
      { find: /^react(?=\/|$)/, replacement: `${frontendModules}/react` },
      { find: /^lucide-react$/, replacement: `${frontendModules}/lucide-react` },
    ],
  },
})
