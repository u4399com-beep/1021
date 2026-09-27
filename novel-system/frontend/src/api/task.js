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
}
