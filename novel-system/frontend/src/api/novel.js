import http from '@/api'

export const novelApi = {
  list: (params) => http.get('/novels/books/', { params }),
  detail: (id) => http.get(`/novels/books/${id}/`),
  create: (data) => http.post('/novels/books/', data),
  update: (id, data) => http.patch(`/novels/books/${id}/`, data),
  delete: (id) => http.delete(`/novels/books/${id}/soft_delete/`),
  republish: (id) => http.post(`/novels/books/${id}/republish/`),
  listCategories: (params) => http.get('/novels/categories/', { params }),
  categoryTree: () => http.get('/novels/categories/tree/'),
  createCategory: (data) => http.post('/novels/categories/', data),
  listAuthors: (params) => http.get('/novels/authors/', { params }),
  listTags: (params) => http.get('/novels/tags/', { params }),
  listSuggestKeywords: (params) => http.get('/novels/suggest-keywords/', { params }),
}
