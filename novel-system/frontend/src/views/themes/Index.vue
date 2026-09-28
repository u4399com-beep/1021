<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>主题模板</template>
      <el-row :gutter="16">
        <el-col :span="8" v-for="t in themes" :key="t.id">
          <el-card class="theme-card" shadow="hover">
            <div class="theme-cover" :style="{ background: gradient(t.code) }">
              <div class="theme-name">{{ t.name }}</div>
            </div>
            <div class="theme-info">
              <p class="theme-desc">{{ t.description }}</p>
              <p class="theme-code">代码: <code>{{ t.code }}</code></p>
              <p>已用于 {{ t.sites_count || 0 }} 个站点</p>
              <el-button type="primary" plain @click="preview(t)">查看示例</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>

    <el-dialog v-model="previewVisible" title="主题预览" width="90%" top="5vh">
      <iframe :src="previewUrl" style="width: 100%; height: 70vh; border: 0;" sandbox="allow-same-origin" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { themeApi } from '@/api/site'

const themes = ref([])
const previewVisible = ref(false)
const previewUrl = ref('')

const gradientMap = {
  simple_reading: 'linear-gradient(135deg, #fafafa 0%, #e8e8e8 100%)',
  classic_shelf: 'linear-gradient(135deg, #8b4513 0%, #d2691e 100%)',
  magazine_modern: 'linear-gradient(135deg, #ff6b6b 0%, #feca57 100%)',
  dark_tech: 'linear-gradient(135deg, #0f0c29 0%, #302b63 50%, #24243e 100%)',
  minimal_rank: 'linear-gradient(135deg, #2c3e50 0%, #4ca1af 100%)',
}
const gradient = (code) => gradientMap[code] || '#f0f0f0'

async function load() {
  const { data } = await themeApi.list()
  themes.value = data.results || data
}

function preview(t) {
  previewUrl.value = `/themes/${t.code}/index.html`
  previewVisible.value = true
}

onMounted(load)
</script>

<style scoped lang="scss">
.theme-card { margin-bottom: 16px; }
.theme-cover {
  height: 140px; border-radius: 8px 8px 0 0;
  display: flex; align-items: center; justify-content: center;
  color: #fff; .theme-name { font-size: 18px; font-weight: 600; text-shadow: 0 1px 4px rgba(0,0,0,.2); }
}
.theme-info { padding: 12px 0; }
.theme-desc { color: #606266; font-size: 13px; margin-bottom: 8px; line-height: 1.6; }
.theme-code { font-size: 12px; color: #909399; code { background: #f4f4f5; padding: 2px 6px; border-radius: 4px; } }
</style>
