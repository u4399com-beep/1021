import { defineStore } from 'pinia'
import axios from '@/api'

export const useUserStore = defineStore('user', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    refresh: localStorage.getItem('refresh') || '',
    user: null,
  }),
  actions: {
    setToken(accessToken, refreshToken) {
      this.token = accessToken
      this.refresh = refreshToken
      localStorage.setItem('token', accessToken)
      localStorage.setItem('refresh', refreshToken)
    },
    async login(payload) {
      const { data } = await axios.post('/auth/login/', payload)
      this.setToken(data.access, data.refresh)
      return data
    },
    async fetchMe() {
      const { data } = await axios.get('/auth/me/')
      this.user = data
      return data
    },
    async refresh_token() {
      try {
        const { data } = await axios.post('/auth/refresh/', { refresh: this.refresh })
        this.setToken(data.access, data.refresh)
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
      localStorage.removeItem('token')
      localStorage.removeItem('refresh')
    },
    async logout() {
      this.clear()
    },
  },
})
