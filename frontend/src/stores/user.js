import { defineStore } from 'pinia'
import axios from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    refresh: localStorage.getItem('refresh') || '',
    user: null,
    permissions: JSON.parse(localStorage.getItem('perms') || '[]'),
  }),
  getters: {
    hasPermission: (state) => (perm) => {
      if (!state.user) return false
      if (state.user.is_superuser_user || state.user.is_superuser) return true
      return state.permissions.includes(perm)
    },
    hasAnyPermission: (state) => (perms) => {
      if (!state.user) return false
      if (state.user.is_superuser_user || state.user.is_superuser) return true
      return perms.some(p => state.permissions.includes(p))
    },
  },
  actions: {
    setToken(accessToken, refreshToken) {
      this.token = accessToken
      this.refresh = refreshToken
      localStorage.setItem('token', accessToken)
      localStorage.setItem('refresh', refreshToken)
    },
    setPermissions(perms) {
      this.permissions = perms || []
      localStorage.setItem('perms', JSON.stringify(this.permissions))
    },
    async login(payload) {
      const { data } = await axios.post('/auth/login/', payload)
      this.setToken(data.access, data.refresh)
      // JWT tokens carry permissions claim; decode it
      try {
        const payload = JSON.parse(atob(data.access.split('.')[1]))
        this.setPermissions(payload.permissions || [])
      } catch (e) {
        this.setPermissions([])
      }
      return data
    },
    async fetchMe() {
      const { data } = await axios.get('/auth/me/')
      this.user = data
      // Sync permissions from API response (UserSerializer.permission_codes)
      if (data.permission_codes) {
        this.setPermissions(data.permission_codes)
      }
      return data
    },
    async refresh_token() {
      try {
        const { data } = await axios.post('/auth/refresh/', { refresh: this.refresh })
        this.setToken(data.access, data.refresh)
        try {
          const payload = JSON.parse(atob(data.access.split('.')[1]))
          this.setPermissions(payload.permissions || [])
        } catch (e) {}
        return data.access
      } catch (e) {
        this.clear()
        throw e
      }
    },
    clear() {
      this.token = ''
      this.refresh = ''
      this.user = null
      this.permissions = []
      localStorage.removeItem('token')
      localStorage.removeItem('refresh')
      localStorage.removeItem('perms')
    },
    async logout() {
      this.clear()
    },
  },
})
