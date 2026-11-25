import { defineStore } from 'pinia'

const KEY = 'avm_theme'

function readStored() {
  try {
    const v = localStorage.getItem(KEY)
    if (v === 'light' || v === 'dark') return v
  } catch (e) {
    /* localStorage 不可用时退回系统偏好 */
  }
  if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) return 'dark'
  return 'light'
}

export const useThemeStore = defineStore('theme', {
  state: () => ({
    theme: readStored()
  }),
  getters: {
    isDark: (s) => s.theme === 'dark'
  },
  actions: {
    apply() {
      const dark = this.theme === 'dark'
      document.documentElement.classList.toggle('dark', dark)
      document.documentElement.setAttribute('data-theme', this.theme)
    },
    set(theme) {
      this.theme = theme === 'dark' ? 'dark' : 'light'
      this.apply()
      try {
        localStorage.setItem(KEY, this.theme)
      } catch (e) {
        /* 忽略存储异常 */
      }
    },
    toggle() {
      this.set(this.theme === 'dark' ? 'light' : 'dark')
    }
  }
})
