import { defineStore } from 'pinia'
import { api } from '../api'
import { normalizeOption } from '../api/platforms'

// 兼容旧配置：display 可能是 { mode: 'full' }，也可能是裸字符串
function readMode(value) {
  const mode = value && typeof value === 'object' ? value.mode : value
  return mode === 'label' || mode === 'icon' ? mode : 'full'
}

export const useSettingsStore = defineStore('settings', {
  state: () => ({
    items: {
      site: { name: '视频资产管理', subtitle: 'Assets Console', logo: '' },
      douyin: {},
      welcome: { city: '深圳', latitude: null, longitude: null },
      vote: { daily_limit: 5 },
      platforms: [],
      publish_platforms: [],
      publish_accounts: [],
      // 三个模块各自的统一显示方式：full 全显 / label 标签 / icon 图标
      // 集中存于 platform_display 键：{ mode, category, platform, publish }
      platform_display: { mode: 'full', category: 'full', platform: 'full', publish: 'full' },
      categories: []
    },
    loaded: false
  }),
  getters: {
    siteName: (s) => s.items.site?.name || '视频资产管理',
    siteSubtitle: (s) => s.items.site?.subtitle || 'Assets Console',
    douyin: (s) => s.items.douyin || {},
    welcome: (s) => s.items.welcome || { city: '深圳', latitude: null, longitude: null },
    vote: (s) => s.items.vote || { daily_limit: 5 },
    platforms: (s) => s.items.platforms || [],
    publishPlatforms: (s) => s.items.publish_platforms || [],
    publishAccounts: (s) => s.items.publish_accounts || [],
    categories: (s) => s.items.categories || [],
    // 视频分类固定使用 full 样式：首字颜色底白字方块 + 后面完整颜色文字（不用图标、不显示方式切换）
    categoryDisplayMode: () => 'full',
    // 制作 / 发布平台：模块级显示方式，兼容旧的裸 mode 结构
    platformDisplayMode: (s) => readMode((s.items.platform_display || {}).platform ?? (s.items.platform_display || {}).mode),
    publishDisplayMode: (s) => readMode((s.items.platform_display || {}).publish ?? (s.items.platform_display || {}).mode),
    // 统一选项解析：名称 → { name, color, image, display }
    // display 一律使用模块级设置，不再读取单项字段
    platformOptions: (s) => {
      const mode = readMode(s.items.platform_display)
      const items = s.items.platforms || []
      const fallback = [
        { name: '硬核', color: '#4a7cc4', image: '', display: mode },
        { name: '小云雀', color: '#7b62c9', image: '', display: mode },
        { name: '三方平台', color: '#3da377', image: '', display: mode }
      ]
      if (!items.length) return fallback
      return items.map((p) => ({ ...normalizeOption(p, '#4a7cc4'), display: mode }))
    },
    publishPlatformOptions: (s) => {
      const mode = readMode(s.items.publish_display)
      const items = s.items.publish_platforms || []
      const fallback = [
        { name: '抖音', color: '#e05c4b', image: '', display: mode },
        { name: '小红书', color: '#ff7b6b', image: '', display: mode },
        { name: 'B站', color: '#4a7cc4', image: '', display: mode },
        { name: '视频号', color: '#3da377', image: '', display: mode }
      ]
      if (!items.length) return fallback
      return items.map((p) => ({ ...normalizeOption(p, '#e05c4b'), display: mode }))
    },
    categoryOptions: (s) => {
      // 分类固定为首字色底白字 + 完整颜色文字（full 模式），去掉历史图标
      return (s.items.categories || []).map((c) => ({
        ...normalizeOption(c, '#7b62c9'),
        image: '',
        display: 'full'
      }))
    }
  },
  actions: {
    /** 按名称取选项的展示信息：kind = platform | publish | category */
    option(kind, name) {
      const key = kind === 'publish' ? 'publishPlatformOptions' : kind === 'category' ? 'categoryOptions' : 'platformOptions'
      const mode = kind === 'publish' ? this.publishDisplayMode
        : kind === 'category' ? this.categoryDisplayMode
        : this.platformDisplayMode
      const found = (this[key] || []).find((o) => o.name === name)
      return {
        name: name || '',
        color: found?.color || '#909399',
        // 分类强制无图标：只用首字色块 + 颜色文字
        image: kind === 'category' ? '' : (found?.image || ''),
        display: mode
      }
    },
    async loadCategories() {
      try {
        const { data } = await api.get('/categories')
        this.items = { ...this.items, categories: Array.isArray(data) ? data : [] }
      } catch (e) {
        /* 分类读取失败时保持空，展示回退默认色 */
      }
    },
    async load(force = false) {
      if (this.loaded && !force) return
      try {
        const { data } = await api.get('/settings')
        this.items = { ...this.items, ...data }
        this.loaded = true
      } catch (e) {
        /* 配置读取失败时使用内置默认值 */
      }
      await this.loadCategories()
    },
    async save(key, value) {
      const { data } = await api.put('/settings', { key, value })
      const merged = Array.isArray(value)
        ? value
        : { ...(this.items[key] && !Array.isArray(this.items[key]) ? this.items[key] : {}), ...value }
      this.items = { ...this.items, [key]: merged }
      return data
    }
  }
})
