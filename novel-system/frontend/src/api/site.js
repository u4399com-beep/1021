import http from '@/api'

export const siteApi = {
  list: (params) => http.get('/sites/', { params }),
  detail: (id) => http.get(`/sites/${id}/`),
  create: (data) => http.post('/sites/', data),
  update: (id, data) => http.patch(`/sites/${id}/`, data),
  delete: (id) => http.delete(`/sites/${id}/`),
  regenerateNginx: (id) => http.post(`/sites/${id}/regenerate_nginx/`),

  listThemes: () => http.get('/sites/themes/'),
  previewTheme: (id) => http.post(`/sites/themes/${id}/preview/`),
}

export const themeApi = {
  list: () => http.get('/themes/'),
  files: (id) => http.get(`/themes/${id}/files/`),
  render: (id, data) => http.post(`/themes/${id}/render/`, data),
}
