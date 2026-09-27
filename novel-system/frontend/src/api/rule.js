import http from '@/api'

export const ruleApi = {
  list: (params) => http.get('/rules/', { params }),
  detail: (id) => http.get(`/rules/${id}/`),
  create: (data) => http.post('/rules/', data),
  update: (id, data) => http.patch(`/rules/${id}/`, data),
  delete: (id) => http.delete(`/rules/${id}/`),
  enable: (id) => http.post(`/rules/${id}/enable/`),
  disable: (id) => http.post(`/rules/${id}/disable/`),
  test: (data) => http.post('/rules/test/', data),

  listSources: (params) => http.get('/rules/sources/', { params }),
  createSource: (data) => http.post('/rules/sources/', data),
  updateSource: (id, data) => http.patch(`/rules/sources/${id}/`, data),
  deleteSource: (id) => http.delete(`/rules/sources/${id}/`),
}
