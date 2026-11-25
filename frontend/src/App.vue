<template>
  <router-view />
</template>

<script setup>
import { watch } from 'vue'
import { useRoute } from 'vue-router'
import { useThemeStore } from './stores/theme'

const theme = useThemeStore()
const route = useRoute()

// 登录页有独立的浅色视觉，不跟随全局主题；其余页面按用户选择应用
watch(
  () => route.path,
  (path) => {
    if (path === '/login') {
      document.documentElement.classList.remove('dark')
      document.documentElement.setAttribute('data-theme', 'light')
    } else {
      theme.apply()
    }
  },
  { immediate: true }
)
</script>
