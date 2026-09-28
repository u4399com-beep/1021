import http from '@/api'

export const obfuscatorApi = {
  // Profile
  listProfiles: (params) => http.get('/obfuscator/profiles/', { params }),
  createProfile: (data) => http.post('/obfuscator/profiles/', data),
  updateProfile: (id, data) => http.patch(`/obfuscator/profiles/${id}/`, data),
  enableForSite: (siteId) => http.post('/obfuscator/profiles/enable-for-site/', { site_id: siteId }),
  disableForSite: (siteId) => http.post('/obfuscator/profiles/disable-for-site/', { site_id: siteId }),
  // Synonyms
  listSynonyms: (params) => http.get('/obfuscator/synonyms/', { params }),
  createSynonym: (data) => http.post('/obfuscator/synonyms/', data),
  updateSynonym: (id, data) => http.patch(`/obfuscator/synonyms/${id}/`, data),
  deleteSynonym: (id) => http.delete(`/obfuscator/synonyms/${id}/`),
  bulkCreateSynonyms: (items) => http.post('/obfuscator/synonyms/bulk/', { items }),
  // Interference sentences
  listInterferences: (params) => http.get('/obfuscator/interferences/', { params }),
  createInterference: (data) => http.post('/obfuscator/interferences/', data),
  updateInterference: (id, data) => http.patch(`/obfuscator/interferences/${id}/`, data),
  deleteInterference: (id) => http.delete(`/obfuscator/interferences/${id}/`),
  // Preview / Diff
  preview: (data) => http.post('/obfuscator/preview/preview/', data),
  diff: (data) => http.post('/obfuscator/preview/diff/', data),
  visualDiff: (data) => http.post('/obfuscator/preview/visual-diff/', data),
}

export const volumeApi = {
  list: (params) => http.get('/novels/volumes/', { params }),
  create: (data) => http.post('/novels/volumes/', data),
  update: (id, data) => http.patch(`/novels/volumes/${id}/`, data),
  delete: (id) => http.delete(`/novels/volumes/${id}/`),
  assignChapters: (id, chapterIds) => http.post(`/novels/volumes/${id}/assign_chapters/`, { chapter_ids: chapterIds }),
  autoSplit: (id, count, prefix) => http.post(`/novels/volumes/${id}/auto_split_by_count/`, { count, prefix }),
}

export const disorderCheckApi = {
  check: (bookId) => http.get(`/novels/books/${bookId}/disorder_check/`),
}
