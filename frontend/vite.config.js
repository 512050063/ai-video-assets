import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  // 每次构建写入时间戳，页面上可见，便于确认浏览器加载的是不是最新前端
  define: {
    __APP_BUILD_TIME__: JSON.stringify(new Date().toISOString()),
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/uploads': { target: 'http://127.0.0.1:8000', changeOrigin: true }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/element-plus') || id.includes('node_modules/@element-plus')) {
            return 'element-plus'
          }
          if (id.includes('node_modules/vue') || id.includes('node_modules/pinia')) {
            return 'vue-vendor'
          }
        }
      }
    }
  }
})
