import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  // Dev-only: Member 2 (8005) and Member 4 (8004) have no/partial CORS setup,
  // so the browser reaches them through the Vite dev server instead.
  server: {
    proxy: {
      '/member2': {
        target: 'http://127.0.0.1:8005',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/member2/, ''),
      },
      '/member4': {
        target: 'http://127.0.0.1:8004',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/member4/, ''),
      },
    },
  },
})
