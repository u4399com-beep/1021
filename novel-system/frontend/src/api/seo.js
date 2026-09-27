import http from '@/api'

export const seoApi = {
  // Audit
  auditAll: () => http.get('/seo/audit/'),
  auditOne: (siteId) => http.get(`/seo/audit/${siteId}/`),
  regenSitemaps: () => http.post('/seo/regenerate-sitemaps/'),

  // Direct sitemap / RSS URLs (for preview iframe)
  sitemapUrl: (host) => `/sitemap.xml`,
  rssUrl: (host) => `/rss.xml`,
  bookRssUrl: (slug) => `/book/${slug}/rss.xml`,
}
