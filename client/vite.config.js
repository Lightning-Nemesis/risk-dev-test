import { defineConfig, loadEnv } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig(({ mode }) => {
  // Vite doesn't load .env while reading this file, so load it here.
  // Variables already set in the environment (e.g. by Docker) take priority over client/.env.
  const env = loadEnv(mode, process.cwd(), '')
  if (!env.API_URL) {
    throw new Error('API_URL is not set. Add it to client/.env')
  }

  return {
    plugins: [vue()],
    server: {
      port: 5173,
      strictPort: true, // stop with a clear error if the port is taken, instead of moving to another one
      proxy: {
        // The browser calls /api/... on this dev server, which forwards the request to the Flask server
        '/api': env.API_URL,
      },
    },
  }
})
