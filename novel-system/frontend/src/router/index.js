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
      { path: 'novels', name: 'novels', component: () => import('@/views/novels/Index.vue'), meta: { title: '小说管理', icon: 'Reading' } },
      { path: 'novels/:id', name: 'novel-detail', component: () => import('@/views/novels/Detail.vue'), meta: { title: '小说详情', hidden: true } },
      { path: 'rules', name: 'rules', component: () => import('@/views/rules/Index.vue'), meta: { title: '采集规则', icon: 'Document' } },
      { path: 'rules/:id/edit', name: 'rule-edit', component: () => import('@/views/rules/Editor.vue'), meta: { title: '规则编辑', hidden: true } },
      { path: 'rules/new', name: 'rule-new', component: () => import('@/views/rules/Editor.vue'), meta: { title: '新建规则', hidden: true } },
      { path: 'tasks', name: 'tasks', component: () => import('@/views/tasks/Index.vue'), meta: { title: '采集任务', icon: 'List' } },
      { path: 'tasks/:id', name: 'task-detail', component: () => import('@/views/tasks/Detail.vue'), meta: { title: '任务详情', hidden: true } },
      { path: 'cleaner', name: 'cleaner', component: () => import('@/views/cleaner/Index.vue'), meta: { title: '内容清洗', icon: 'Brush' } },
      { path: 'classifier', name: 'classifier', component: () => import('@/views/classifier/Index.vue'), meta: { title: '智能分类', icon: 'MagicStick' } },
      { path: 'sites', name: 'sites', component: () => import('@/views/sites/Index.vue'), meta: { title: '站群管理', icon: 'Connection' } },
      { path: 'sites/:id/edit', name: 'site-edit', component: () => import('@/views/sites/Editor.vue'), meta: { title: '编辑站点', hidden: true } },
      { path: 'themes', name: 'themes', component: () => import('@/views/themes/Index.vue'), meta: { title: '主题模板', icon: 'Picture' } },
      { path: 'downloads', name: 'downloads', component: () => import('@/views/downloads/Index.vue'), meta: { title: '文件下载', icon: 'Download' } },
      { path: 'system', name: 'system', component: () => import('@/views/system/Index.vue'), meta: { title: '系统设置', icon: 'Setting' } },
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
  next()
})

router.afterEach(() => {
  NProgress.done()
})

export default router
