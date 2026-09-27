<template>
  <el-container class="admin-layout">
    <el-aside :width="isCollapse ? '64px' : '220px'" class="sidebar">
      <div class="logo">
        <span v-if="!isCollapse">小说管理系统</span>
        <span v-else>NS</span>
      </div>
      <el-menu
        :default-active="$route.path"
        :collapse="isCollapse"
        :collapse-transition="false"
        router
        background-color="#1f2937"
        text-color="#cbd5e1"
        active-text-color="#fff"
      >
        <template v-for="r in menuItems" :key="r.path">
          <el-menu-item :index="r.path">
            <el-icon><component :is="r.icon" /></el-icon>
            <template #title>{{ r.title }}</template>
          </el-menu-item>
        </template>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="header">
        <div class="header-left">
          <el-icon class="toggle-btn" @click="isCollapse = !isCollapse">
            <Fold v-if="!isCollapse" />
            <Expand v-else />
          </el-icon>
          <el-breadcrumb separator="/">
            <el-breadcrumb-item :to="{ path: '/admin/dashboard' }">首页</el-breadcrumb-item>
            <el-breadcrumb-item>{{ $route.meta.title }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>
        <div class="header-right">
          <el-dropdown @command="onCommand">
            <span class="user-info">
              <el-avatar :size="28" :src="userStore.user?.avatar">{{ userStore.user?.username?.[0]?.toUpperCase() }}</el-avatar>
              <span style="margin-left: 8px;">{{ userStore.user?.nickname || userStore.user?.username }}</span>
            </span>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">个人资料</el-dropdown-item>
                <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </el-header>

      <el-main class="main">
        <router-view v-slot="{ Component }">
          <transition name="fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { ElMessageBox } from 'element-plus'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()
const isCollapse = ref(false)

const menuItems = computed(() => router.options.routes
  .find(r => r.path === '/admin')?.children || []
  .filter(r => !r.meta?.hidden)
  .map(r => ({
    path: `/admin${r.path === '' ? '' : '/' + r.path}`.replace(/\/+/g, '/'),
    title: r.meta?.title || r.name,
    icon: r.meta?.icon || 'Menu',
  })))

async function onCommand(cmd) {
  if (cmd === 'logout') {
    await ElMessageBox.confirm('确定要退出登录吗？', '提示', { type: 'warning' })
    await userStore.logout()
    router.push({ name: 'login' })
  } else if (cmd === 'profile') {
    ElMessage.info('个人资料功能开发中')
  }
}
</script>

<style scoped lang="scss">
.admin-layout { height: 100vh; }

.sidebar {
  background: #1f2937;
  color: #fff;
  transition: width 0.2s;
  overflow: hidden;

  .logo {
    height: 60px;
    line-height: 60px;
    text-align: center;
    font-weight: 600;
    font-size: 16px;
    color: #fff;
    background: #111827;
    border-bottom: 1px solid rgba(255, 255, 255, 0.05);
  }
  :deep(.el-menu) { border-right: 0; }
}

.header {
  background: #fff;
  border-bottom: 1px solid #e5e7eb;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 16px;

  .header-left, .header-right { display: flex; align-items: center; gap: 16px; }
  .toggle-btn { cursor: pointer; font-size: 18px; }
  .user-info { display: flex; align-items: center; cursor: pointer; }
}

.main { background: #f5f7fa; padding: 16px; overflow-y: auto; }

.fade-enter-active, .fade-leave-active { transition: opacity 0.15s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
