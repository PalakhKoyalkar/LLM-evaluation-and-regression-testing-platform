import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    host: true,
    // Locally the API runs on 8010 (8000 is taken by another stack); in Docker, API_URL is set.
    proxy: { '/api': process.env.API_URL ?? 'http://localhost:8010' },
  },
})
