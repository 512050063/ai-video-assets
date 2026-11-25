import { defineStore } from 'pinia'
import { api } from '../api'
import { readToken } from '../utils/session'

/* 模块角色权限
 * 与后端 backend/app/permissions.py 保持一致：
 * - menus：可见菜单（对应前端路由 name）
 * - buttons：可用按钮（`模块.动作` 形式）
 * 超管恒为全量权限。
 */
export const usePermissionStore = defineStore('permission', {
  state: () => ({
    loaded: false,
    role: 'production',
    roleName: '',
    menus: [],
    buttons: [],
    // 角色定义与可勾选目录（超管在「角色权限」页查看/调整）
    roles: [],
    catalog: { menus: [], buttons: [] }
  }),
  getters: {
    isSuper: (s) => s.role === 'super',
    // 菜单可见性
    canMenu: (s) => (key) => s.role === 'super' || s.menus.includes(key),
    // 按钮可用性
    can: (s) => (key) => s.role === 'super' || s.buttons.includes(key),
    // 角色定义按 key 索引
    roleMap: (s) => {
      const map = {}
      s.roles.forEach((r) => { map[r.key] = r })
      return map
    }
  },
  actions: {
    async load(force = false) {
      if (this.loaded && !force) return
      // 未登录时不请求权限接口（否则会触发 401 跳登录页）
      if (!readToken()) {
        this.loaded = true
        return
      }
      try {
        const { data } = await api.get('/roles/mine')
        this.role = data.role || 'production'
        this.roleName = data.role_name || ''
        this.menus = Array.isArray(data.menus) ? data.menus : []
        this.buttons = Array.isArray(data.buttons) ? data.buttons : []
        this.loaded = true
      } catch (e) {
        /* 权限读取失败时保持空权限，由后端做最终校验 */
        this.loaded = true
      }
    },
    async loadRoles(force = false) {
      try {
        const { data } = await api.get('/roles')
        this.roles = Array.isArray(data) ? data : []
        if (force) {
          const { data: catalog } = await api.get('/roles/catalog')
          this.catalog = catalog || { menus: [], buttons: [] }
        }
      } catch (e) {
        this.roles = []
      }
    },
    async saveRole(roleKey, payload) {
      const { data } = await api.put(`/roles/${roleKey}`, payload)
      await this.loadRoles(true)
      return data
    },
    async assignUser(userId, moduleRole) {
      const { data } = await api.put(`/roles/users/${userId}`, { module_role: moduleRole })
      return data
    },
    reset() {
      this.loaded = false
      this.role = 'production'
      this.roleName = ''
      this.menus = []
      this.buttons = []
    }
  }
})
