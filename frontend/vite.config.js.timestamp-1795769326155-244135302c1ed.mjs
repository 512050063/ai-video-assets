// vite.config.js
import { defineConfig } from "file:///D:/project/AssetsConsole/frontend/node_modules/vite/dist/node/index.js";
import vue from "file:///D:/project/AssetsConsole/frontend/node_modules/@vitejs/plugin-vue/dist/index.mjs";
var vite_config_default = defineConfig({
  plugins: [vue()],
  // 每次构建写入时间戳，页面上可见，便于确认浏览器加载的是不是最新前端
  define: {
    __APP_BUILD_TIME__: JSON.stringify((/* @__PURE__ */ new Date()).toISOString())
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://127.0.0.1:8000", changeOrigin: true },
      "/uploads": { target: "http://127.0.0.1:8000", changeOrigin: true }
    }
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes("node_modules/element-plus") || id.includes("node_modules/@element-plus")) {
            return "element-plus";
          }
          if (id.includes("node_modules/vue") || id.includes("node_modules/pinia")) {
            return "vue-vendor";
          }
        }
      }
    }
  }
});
export {
  vite_config_default as default
};
//# sourceMappingURL=data:application/json;base64,ewogICJ2ZXJzaW9uIjogMywKICAic291cmNlcyI6IFsidml0ZS5jb25maWcuanMiXSwKICAic291cmNlc0NvbnRlbnQiOiBbImNvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9kaXJuYW1lID0gXCJEOlxcXFxwcm9qZWN0XFxcXEFzc2V0c0NvbnNvbGVcXFxcZnJvbnRlbmRcIjtjb25zdCBfX3ZpdGVfaW5qZWN0ZWRfb3JpZ2luYWxfZmlsZW5hbWUgPSBcIkQ6XFxcXHByb2plY3RcXFxcQXNzZXRzQ29uc29sZVxcXFxmcm9udGVuZFxcXFx2aXRlLmNvbmZpZy5qc1wiO2NvbnN0IF9fdml0ZV9pbmplY3RlZF9vcmlnaW5hbF9pbXBvcnRfbWV0YV91cmwgPSBcImZpbGU6Ly8vRDovcHJvamVjdC9Bc3NldHNDb25zb2xlL2Zyb250ZW5kL3ZpdGUuY29uZmlnLmpzXCI7aW1wb3J0IHsgZGVmaW5lQ29uZmlnIH0gZnJvbSAndml0ZSdcbmltcG9ydCB2dWUgZnJvbSAnQHZpdGVqcy9wbHVnaW4tdnVlJ1xuXG5leHBvcnQgZGVmYXVsdCBkZWZpbmVDb25maWcoe1xuICBwbHVnaW5zOiBbdnVlKCldLFxuICAvLyBcdTZCQ0ZcdTZCMjFcdTY3ODRcdTVFRkFcdTUxOTlcdTUxNjVcdTY1RjZcdTk1RjRcdTYyMzNcdUZGMENcdTk4NzVcdTk3NjJcdTRFMEFcdTUzRUZcdTg5QzFcdUZGMENcdTRGQkZcdTRFOEVcdTc4NkVcdThCQTRcdTZENEZcdTg5QzhcdTU2NjhcdTUyQTBcdThGN0RcdTc2ODRcdTY2MkZcdTRFMERcdTY2MkZcdTY3MDBcdTY1QjBcdTUyNERcdTdBRUZcbiAgZGVmaW5lOiB7XG4gICAgX19BUFBfQlVJTERfVElNRV9fOiBKU09OLnN0cmluZ2lmeShuZXcgRGF0ZSgpLnRvSVNPU3RyaW5nKCkpLFxuICB9LFxuICBzZXJ2ZXI6IHtcbiAgICBwb3J0OiA1MTczLFxuICAgIHByb3h5OiB7XG4gICAgICAnL2FwaSc6IHsgdGFyZ2V0OiAnaHR0cDovLzEyNy4wLjAuMTo4MDAwJywgY2hhbmdlT3JpZ2luOiB0cnVlIH0sXG4gICAgICAnL3VwbG9hZHMnOiB7IHRhcmdldDogJ2h0dHA6Ly8xMjcuMC4wLjE6ODAwMCcsIGNoYW5nZU9yaWdpbjogdHJ1ZSB9XG4gICAgfVxuICB9LFxuICBidWlsZDoge1xuICAgIHJvbGx1cE9wdGlvbnM6IHtcbiAgICAgIG91dHB1dDoge1xuICAgICAgICBtYW51YWxDaHVua3MoaWQpIHtcbiAgICAgICAgICBpZiAoaWQuaW5jbHVkZXMoJ25vZGVfbW9kdWxlcy9lbGVtZW50LXBsdXMnKSB8fCBpZC5pbmNsdWRlcygnbm9kZV9tb2R1bGVzL0BlbGVtZW50LXBsdXMnKSkge1xuICAgICAgICAgICAgcmV0dXJuICdlbGVtZW50LXBsdXMnXG4gICAgICAgICAgfVxuICAgICAgICAgIGlmIChpZC5pbmNsdWRlcygnbm9kZV9tb2R1bGVzL3Z1ZScpIHx8IGlkLmluY2x1ZGVzKCdub2RlX21vZHVsZXMvcGluaWEnKSkge1xuICAgICAgICAgICAgcmV0dXJuICd2dWUtdmVuZG9yJ1xuICAgICAgICAgIH1cbiAgICAgICAgfVxuICAgICAgfVxuICAgIH1cbiAgfVxufSlcbiJdLAogICJtYXBwaW5ncyI6ICI7QUFBNlIsU0FBUyxvQkFBb0I7QUFDMVQsT0FBTyxTQUFTO0FBRWhCLElBQU8sc0JBQVEsYUFBYTtBQUFBLEVBQzFCLFNBQVMsQ0FBQyxJQUFJLENBQUM7QUFBQTtBQUFBLEVBRWYsUUFBUTtBQUFBLElBQ04sb0JBQW9CLEtBQUssV0FBVSxvQkFBSSxLQUFLLEdBQUUsWUFBWSxDQUFDO0FBQUEsRUFDN0Q7QUFBQSxFQUNBLFFBQVE7QUFBQSxJQUNOLE1BQU07QUFBQSxJQUNOLE9BQU87QUFBQSxNQUNMLFFBQVEsRUFBRSxRQUFRLHlCQUF5QixjQUFjLEtBQUs7QUFBQSxNQUM5RCxZQUFZLEVBQUUsUUFBUSx5QkFBeUIsY0FBYyxLQUFLO0FBQUEsSUFDcEU7QUFBQSxFQUNGO0FBQUEsRUFDQSxPQUFPO0FBQUEsSUFDTCxlQUFlO0FBQUEsTUFDYixRQUFRO0FBQUEsUUFDTixhQUFhLElBQUk7QUFDZixjQUFJLEdBQUcsU0FBUywyQkFBMkIsS0FBSyxHQUFHLFNBQVMsNEJBQTRCLEdBQUc7QUFDekYsbUJBQU87QUFBQSxVQUNUO0FBQ0EsY0FBSSxHQUFHLFNBQVMsa0JBQWtCLEtBQUssR0FBRyxTQUFTLG9CQUFvQixHQUFHO0FBQ3hFLG1CQUFPO0FBQUEsVUFDVDtBQUFBLFFBQ0Y7QUFBQSxNQUNGO0FBQUEsSUFDRjtBQUFBLEVBQ0Y7QUFDRixDQUFDOyIsCiAgIm5hbWVzIjogW10KfQo=
