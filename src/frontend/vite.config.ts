import { defineConfig, loadEnv } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import path from 'path'

// https://vite.dev/config/
export default defineConfig(({ mode }) => {
  const projectRoot = path.resolve(import.meta.dirname, '../..')
  const env = loadEnv(mode, projectRoot, '')
  const proxyTarget =
    env.VITE_BACKEND_PROXY_TARGET?.trim() ||
    env.VITE_API_URL?.trim() ||
    env.VITE_API_BASE_URL?.trim() ||
    'http://127.0.0.1:8000'

  return {
    // The repository keeps one root .env for backend, worker and frontend.
    // Without envDir, Vite only searches src/frontend and VITE_API_URL is lost.
    envDir: projectRoot,
    plugins: [react(), tailwindcss()],
    resolve: {
      alias: {
        '@': path.resolve(import.meta.dirname, './src'),
      },
    },
    build: {
      chunkSizeWarningLimit: 600,
      rollupOptions: {
        output: {
          manualChunks(id) {
            if (!id.includes("node_modules")) return undefined
            if (id.includes("@livekit") || id.includes("livekit-client")) return "livekit"
            if (id.includes("@tanstack/react-query")) return "query"
            if (id.includes("react-hook-form") || id.includes("@hookform") || id.includes("/zod/")) return "form"
            if (id.includes("/react/") || id.includes("/react-dom/") || id.includes("/react-router-dom/")) return "vendor"
            return undefined
          },
        },
      },
    },
    server: {
      proxy: {
        '/api': {
          target: proxyTarget,
          changeOrigin: true,
        },
      },
    },
  }
})
