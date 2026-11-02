/// <reference types="vitest/config" />
import { fileURLToPath } from 'node:url';

import tailwindcss from '@tailwindcss/vite';
import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

// Khi phát triển: chuyển /api và /ws sang backend FastAPI chạy local (python -m app)
const BACKEND = 'http://127.0.0.1:8765';

export default defineConfig({
  plugins: [react(), tailwindcss()],
  resolve: { alias: { '@': fileURLToPath(new URL('./src', import.meta.url)) } },
  base: './', // app desktop nạp file từ ổ đĩa → đường dẫn tương đối
  server: {
    port: 5173,
    proxy: {
      '/api': BACKEND,
      '/ws': { target: BACKEND.replace('http', 'ws'), ws: true },
    },
  },
  build: {
    outDir: 'dist',
    sourcemap: false,
    rollupOptions: {
      output: {
        manualChunks: { charts: ['recharts'], vendor: ['react', 'react-dom', 'react-router-dom', 'zustand', 'axios'] },
      },
    },
  },
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
});
