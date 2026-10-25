import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig({
  // Относительные пути активов: работает и в Docker (nginx на "/"), и на GitHub Pages
  // (проектный сайт username.github.io/Alfa_Hack/).
  base: './',
  plugins: [react(), tailwindcss()],
  server: {
    port: 3000,
    proxy: {
      // В dev-режиме проксируем API на локальный backend.
      '/api': 'http://localhost:8000',
    },
  },
})
