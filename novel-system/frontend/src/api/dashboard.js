import http from '@/api'

export const dashboardApi = {
  get: () => http.get('/'),
  // Dashboard stats — actually lives on /api/v1/ root
  getStats: () => http.get('/dashboard/'),
  getSystem: () => http.get('/system/'),
}
