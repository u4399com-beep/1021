import http from '@/api'

export const taskApi = {
  list: (params) => http.get('/tasks/', { params }),
  detail: (id) => http.get(`/tasks/${id}/`),
  create: (data) => http.post('/tasks/', data),
  update: (id, data) => http.patch(`/tasks/${id}/`, data),
  delete: (id) => http.delete(`/tasks/${id}/`),
  run: (id) => http.post(`/tasks/${id}/run/`),
  pause: (id) => http.post(`/tasks/${id}/pause/`),
  stop: (id) => http.post(`/tasks/${id}/stop/`),
  updateParams: (id, data) => http.post(`/tasks/${id}/update_params/`, data),
  logs: (id) => http.get(`/tasks/${id}/logs/`),
  progress: (id) => http.get(`/tasks/${id}/progress/`),
  // Schedule management
  setSchedule: (id, data) => http.post(`/tasks/${id}/set_schedule/`, data),
  disableSchedule: (id) => http.post(`/tasks/${id}/disable_schedule/`),
  schedulePreview: (id) => http.get(`/tasks/${id}/schedule_preview/`),
}

export const proxyApi = {
  list: (params) => http.get('/crawler/proxy-pool/', { params }),
  create: (data) => http.post('/crawler/proxy-pool/', data),
  update: (id, data) => http.patch(`/crawler/proxy-pool/${id}/`, data),
  delete: (id) => http.delete(`/crawler/proxy-pool/${id}/`),
  checkAll: (testUrl) => http.post('/crawler/proxy-pool/check_all/', { test_url: testUrl }),
}

export const hyperbrowserApi = {
  status: () => http.get('/crawler/hyperbrowser/status/'),
  create: () => http.post('/crawler/hyperbrowser/create-session/', {}),
  release: (sid) => http.post('/crawler/hyperbrowser/release-session/', { session_id: sid }),
}
