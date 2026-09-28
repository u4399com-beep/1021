import http from '@/api'

export const cleanerApi = {
  listRules: (params) => http.get('/cleaner/rules/', { params }),
  createRule: (data) => http.post('/cleaner/rules/', data),
  updateRule: (id, data) => http.patch(`/cleaner/rules/${id}/`, data),
  deleteRule: (id) => http.delete(`/cleaner/rules/${id}/`),
  preview: (data) => http.post('/cleaner/rules/preview/', data),
  listExecutions: (params) => http.get('/cleaner/executions/', { params }),
}

export const classifierApi = {
  listKeywords: (params) => http.get('/classifier/category-keywords/', { params }),
  createKeyword: (data) => http.post('/classifier/category-keywords/', data),
  deleteKeyword: (id) => http.delete(`/classifier/category-keywords/${id}/`),
  listPatterns: (params) => http.get('/classifier/finished-patterns/', { params }),
  createPattern: (data) => http.post('/classifier/finished-patterns/', data),
  deletePattern: (id) => http.delete(`/classifier/finished-patterns/${id}/`),
  testClassify: (data) => http.post('/classifier/test/classify/', data),
  testFinished: (data) => http.post('/classifier/test/finished/', data),
}

export const downloadApi = {
  listTemplates: (params) => http.get('/downloads/templates/', { params }),
  createTemplate: (data) => http.post('/downloads/templates/', data),
  updateTemplate: (id, data) => http.patch(`/downloads/templates/${id}/`, data),
  deleteTemplate: (id) => http.delete(`/downloads/templates/${id}/`),
  listRecords: (params) => http.get('/downloads/records/', { params }),
  generate: (data) => http.post('/downloads/generate/generate/', data),
  downloadFile: (id) => `/api/v1/downloads/records/${id}/download/`,
}

export const suggestApi = {
  get: (params) => http.get('/crawler/suggest/', { params }),
}

// -----------------------------------------------------------
// Crawler engine — tier diagnostics + testing
// -----------------------------------------------------------
export const engineApi = {
  status: () => http.get('/crawler/engine/status/'),
  test: (data) => http.post('/crawler/engine/test/', data),
  fetch: (data) => http.post('/crawler/engine/fetch/', data),
}

// Proxy pool + Hyperbrowser (re-exported from task.js)
export { proxyApi, hyperbrowserApi } from '@/api/task'
