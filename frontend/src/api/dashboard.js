import http from '@/api'

export const dashboardAnalyticsApi = {
  booksAdded: (params) => http.get('/dashboard/books-added/', { params }),
  tasksCompleted: (params) => http.get('/dashboard/tasks-completed/', { params }),
  successRate: (params) => http.get('/dashboard/success-rate/', { params }),
  topBooks: (params) => http.get('/dashboard/top-books/', { params }),
  storage: () => http.get('/dashboard/storage/'),
  summary: () => http.get('/dashboard/summary/'),
  health: () => http.get('/dashboard/health/'),
  quickHealth: () => http.get('/dashboard/health/quick/'),
  backupStatus: () => http.get('/dashboard/backup/status/'),
  triggerBackup: () => http.post('/dashboard/backup/trigger/'),
  listBackups: () => http.get('/dashboard/backup/list/'),
}
