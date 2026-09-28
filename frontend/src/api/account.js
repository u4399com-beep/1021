import http from '@/api'

export const userApi = {
  list: (params) => http.get('/auth/users/', { params }),
  detail: (id) => http.get(`/auth/users/${id}/`),
  create: (data) => http.post('/auth/users/', data),
  update: (id, data) => http.patch(`/auth/users/${id}/`, data),
  delete: (id) => http.delete(`/auth/users/${id}/`),
  assignRoles: (id, roleIds) => http.post(`/auth/users/${id}/assign_roles/`, { role_ids: roleIds }),
  toggleActive: (id) => http.post(`/auth/users/${id}/toggle_active/`),
}

export const roleApi = {
  list: (params) => http.get('/auth/roles/', { params }),
  detail: (id) => http.get(`/auth/roles/${id}/`),
  create: (data) => http.post('/auth/roles/', data),
  update: (id, data) => http.patch(`/auth/roles/${id}/`, data),
  delete: (id) => http.delete(`/auth/roles/${id}/`),
  catalog: () => http.get('/auth/roles/catalog/'),
}

export const permissionApi = {
  list: (params) => http.get('/auth/permissions/', { params }),
}
