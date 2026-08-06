import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// The API and the SPA are served from the same origin in production (FastAPI hosts
// `dist/`), so all client calls are relative. In dev we proxy to the local uvicorn.
export default defineConfig({
  // Static hosts serve the app from a subpath (GitHub Pages: /<repo>/). Same-origin
  // deploys behind FastAPI leave this at "/".
  base: process.env.VITE_BASE ?? '/',
  plugins: [react()],
  server: {
    proxy: {
      '/api': { target: 'http://127.0.0.1:8099', changeOrigin: true },
    },
  },
  build: {
    target: 'es2020',
    cssCodeSplit: false,
    sourcemap: true,
    rollupOptions: {
      output: {
        manualChunks: { react: ['react', 'react-dom'] },
      },
    },
  },
})
