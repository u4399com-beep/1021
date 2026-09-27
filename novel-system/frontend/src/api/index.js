import axios from 'axios'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'
import router from '@/router'

const apiBase = import.meta.env.VITE_API_BASE || '/api/v1'

const instance = axios.create({
  baseURL: apiBase,
  timeout: 30000,
})

instance.interceptors.request.use((config) => {
  const store = useUserStore()
  if (store.token) {
    config.headers.Authorization = `Bearer ${store.token}`
  }
  return config
})

instance.interceptors.response.use(
  (resp) => resp,
  async (err) => {
    const { response } = err
    if (!response) {
      ElMessage.error('网络错误，请检查后端服务是否启动')
      return Promise.reject(err)
    }
    if (response.status === 401) {
      const store = useUserStore()
      // try refresh once
      if (store.refresh && !err.config.__retry) {
        err.config.__retry = true
        try {
          const newAccess = await store.refresh_token()
          err.config.headers.Authorization = `Bearer ${newAccess}`
          return instance.request(err.config)
        } catch (e) {
          store.clear()
          router.push({ name: 'login' })
          return Promise.reject(e)
        }
      }
      store.clear()
      router.push({ name: 'login' })
    } else if (response.status >= 500) {
      ElMessage.error(`服务器错误 ${response.status}: ${response.data?.detail || ''}`)
    } else if (response.status === 400 || response.status === 404) {
      // let the caller handle validation
    } else {
      ElMessage.error(`错误 ${response.status}: ${response.statusText}`)
    }
    return Promise.reject(err)
  },
)

export default instance
