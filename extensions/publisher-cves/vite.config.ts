import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

// https://vite.dev/config/
export default defineConfig({
  base: '',
  plugins: [vue()],
  preview: {
    proxy: {
      "/api": {
        target: "https://localhost:8000",
        changeOrigin: true
      }
    }
  }
})
