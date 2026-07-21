import react from '@vitejs/plugin-react'
import { defineConfig } from 'vitest/config'

const sourcemapEnabled = ['1', 'true', 'yes'].includes(
  (process.env.VITE_SOURCEMAPS ?? '').toLowerCase(),
)

export default defineConfig({
  plugins: [react()],
  build: {
    minify: 'esbuild',
    sourcemap: sourcemapEnabled,
    modulePreload: {
      polyfill: false,
    },
  },
  test: {
    environment: 'jsdom',
    include: ['./tests/**/*.test.{ts,tsx}'],
    setupFiles: ['./tests/setup.ts'],
  },
})
