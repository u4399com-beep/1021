import { createRouter, createWebHistory } from 'vue-router'
import { useUserStore } from '@/stores/user'
import NProgress from 'nprogress'
import 'nprogress/nprogress.css'

NProgress.configure({ showSpinner: false })

const routes = [
  {
    path: '/admin/login',
    name: 'login',
    component: () => import('@/views/Login.vue'),
    meta: { public: true, title: '登录' },
  },
  {
    path: '/admin',
    component: () => import('@/components/layout/AdminLayout.vue'),
    redirect: '/admin/dashboard',
    children: [
      { path: 'dashboard', name: 'dashboard', component: () => import('@/views/dashboard/Index.vue'), meta: { title: '工作台', icon: 'Odometer' } },
      { path: 'analytics', name: 'analytics', component: () => import('@/views/analytics/Index.vue'), meta: { title: '数据看板', icon: 'TrendCharts', perm: 'system.view' } },
      { path: 'novels', name: 'novels', component: () => import('@/views/novels/Index.vue'), meta: { title: '小说管理', icon: 'Reading', perm: 'novel.view' } },
      { path: 'novels/:id', name: 'novel-detail', component: () => import('@/views/novels/Detail.vue'), meta: { title: '小说详情', hidden: true, perm: 'novel.view' } },
      { path: 'rules', name: 'rules', component: () => import('@/views/rules/Index.vue'), meta: { title: '采集规则', icon: 'Document', perm: 'rule.view' } },
      { path: 'rules/:id/edit', name: 'rule-edit', component: () => import('@/views/rules/Editor.vue'), meta: { title: '规则编辑', hidden: true, perm: 'rule.view' } },
      { path: 'rules/new', name: 'rule-new', component: () => import('@/views/rules/Editor.vue'), meta: { title: '新建规则', hidden: true, perm: 'rule.edit' } },
      { path: 'tasks', name: 'tasks', component: () => import('@/views/tasks/Index.vue'), meta: { title: '采集任务', icon: 'List', perm: 'task.view' } },
      { path: 'tasks/:id', name: 'task-detail', component: () => import('@/views/tasks/Detail.vue'), meta: { title: '任务详情', hidden: true, perm: 'task.view' } },
      { path: 'cleaner', name: 'cleaner', component: () => import('@/views/cleaner/Index.vue'), meta: { title: '内容清洗', icon: 'Brush', perm: 'cleaner.edit' } },
      { path: 'classifier', name: 'classifier', component: () => import('@/views/classifier/Index.vue'), meta: { title: '智能分类', icon: 'MagicStick', perm: 'classifier.edit' } },
      { path: 'sites', name: 'sites', component: () => import('@/views/sites/Index.vue'), meta: { title: '站群管理', icon: 'Connection', perm: 'site.manage' } },
      { path: 'sites/:id/edit', name: 'site-edit', component: () => import('@/views/sites/Editor.vue'), meta: { title: '编辑站点', hidden: true, perm: 'site.manage' } },
      { path: 'themes', name: 'themes', component: () => import('@/views/themes/Index.vue'), meta: { title: '主题模板', icon: 'Picture', perm: 'site.manage' } },
      { path: 'downloads', name: 'downloads', component: () => import('@/views/downloads/Index.vue'), meta: { title: '文件下载', icon: 'Download', perm: 'download.manage' } },
      { path: 'seo', name: 'seo', component: () => import('@/views/seo/Index.vue'), meta: { title: 'SEO 检测', icon: 'Search', perm: 'seo.view' } },
      { path: 'obfuscator', name: 'obfuscator', component: () => import('@/views/obfuscator/Index.vue'), meta: { title: '混淆与伪原创', icon: 'Hide', perm: 'system.edit' } },
      { path: 'users', name: 'users', component: () => import('@/views/users/Index.vue'), meta: { title: '用户与权限', icon: 'UserFilled', perm: 'user.manage' } },
      { path: 'system', name: 'system', component: () => import('@/views/system/Index.vue'), meta: { title: '系统设置', icon: 'Setting', perm: 'system.view' } },
    ],
  },
  { path: '/:pathMatch(.*)*', redirect: '/admin/dashboard' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach(async (to, from, next) => {
  NProgress.start()
  document.title = to.meta?.title ? `${to.meta.title} - 小说管理系统` : '小说管理系统'
  const userStore = useUserStore()
  if (to.meta.public) {
    next()
    return
  }
  if (!userStore.token) {
    next({ name: 'login', query: { redirect: to.fullPath } })
    return
  }
  if (!userStore.user) {
    try {
      await userStore.fetchMe()
    } catch (e) {
      userStore.clear()
      next({ name: 'login' })
      return
    }
  }

  // Route-level permission check
  const requiredPerm = to.meta?.perm
  if (requiredPerm && !userStore.hasPermission(requiredPerm)) {
    // Hide menu but route also blocked; show a friendly denial view
    next({ name: 'dashboard' })
    return
  }
  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router
