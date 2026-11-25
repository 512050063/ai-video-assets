import { defineStore } from 'pinia'
import { api } from '../api'
import { activeStore, clearSession, readToken, readUser, safeRemove, safeSet } from '../utils/session'
import { usePermissionStore } from './permission'

export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: readToken(),
    user: readUser()
  }),
  getters: {
    isLoggedIn: (s) => !!s.token,
    isAdmin: (s) => !!s.user && s.user.role === 'admin',
    displayName: (s) => (s.user ? s.user.nickname || s.user.username : ''),
    initial: (s) => {
      const name = s.user ? s.user.nickname || s.user.username : '?'
      return name.slice(0, 1).toUpperCase()
    }
  },
  actions: {
    _save(token, user, remember = true) {
      this.token = token
      this.user = user
      const target = remember ? localStorage : sessionStorage
      const other = remember ? sessionStorage : localStorage
      safeRemove(other, 'avm_token')
      safeRemove(other, 'avm_user')
      safeSet(target, 'avm_token', token)
      safeSet(target, 'avm_user', JSON.stringify(user))
    },
    async login(payload, remember = true) {
      const { data } = await api.post('/auth/login', payload)
      this._save(data.token, data.user, remember)
    },
    async register(payload, remember = true) {
      const { data } = await api.post('/auth/register', payload)
      this._save(data.token, data.user, remember)
    },
    async fetchMe() {
      if (!this.token) return
      try {
        const { data } = await api.get('/auth/me')
        this.user = data
        safeSet(activeStore(), 'avm_user', JSON.stringify(data))
      } catch (e) {
        /* token 失效时由拦截器处理 */
      }
    },
    logout() {
      this.token = ''
      this.user = null
      clearSession()
      // 清空模块角色权限，避免下次登录沿用上一位用户的权限
      try {
        usePermissionStore().reset()
      } catch (e) {
        /* 忽略：权限 store 未初始化时无需清理 */
      }
    }
  }
})
