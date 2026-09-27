<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-header">
        <h1>小说管理系统</h1>
        <p>Novel Management System</p>
      </div>
      <el-form :model="form" :rules="rules" ref="formRef" label-width="0" size="large" @submit.prevent="onSubmit">
        <el-form-item prop="username">
          <el-input v-model="form.username" placeholder="用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item prop="password">
          <el-input v-model="form.password" type="password" placeholder="密码" :prefix-icon="Lock" show-password @keyup.enter="onSubmit" />
        </el-form-item>
        <el-button type="primary" :loading="loading" class="login-btn" @click="onSubmit">登 录</el-button>
      </el-form>
      <p class="hint">默认账号: admin / admin123456</p>
    </div>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { User, Lock } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { ElMessage } from 'element-plus'

const router = useRouter()
const route = useRoute()
const userStore = useUserStore()
const formRef = ref(null)
const loading = ref(false)

const form = reactive({ username: 'admin', password: 'admin123456' })
const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

async function onSubmit() {
  if (!formRef.value) return
  await formRef.value.validate()
  loading.value = true
  try {
    await userStore.login({ username: form.username, password: form.password })
    await userStore.fetchMe()
    ElMessage.success('登录成功')
    router.push(route.query.redirect || '/admin/dashboard')
  } catch (e) {
    ElMessage.error('登录失败，请检查用户名和密码')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped lang="scss">
.login-page {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);

  .login-card {
    background: #fff;
    padding: 40px 36px;
    border-radius: 12px;
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.15);
    width: 400px;

    .login-header {
      text-align: center;
      margin-bottom: 24px;
      h1 { font-size: 22px; color: #303133; }
      p { color: #909399; font-size: 13px; margin-top: 4px; }
    }
    .login-btn { width: 100%; margin-top: 12px; }
    .hint { text-align: center; margin-top: 16px; font-size: 12px; color: #c0c4cc; }
  }
}
</style>
