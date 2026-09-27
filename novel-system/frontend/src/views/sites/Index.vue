<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-3">
          <el-input v-model="filters.q" placeholder="搜索域名/站名" clearable style="width: 240px;" @keyup.enter="loadData" />
          <el-button type="primary" @click="loadData">搜索</el-button>
        </div>
        <el-button type="primary" @click="addDialog = true">新建站点</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="host" label="域名" min-width="180" />
        <el-table-column prop="name" label="站名" min-width="140" />
        <el-table-column prop="theme_name" label="主题" width="140" />
        <el-table-column prop="offset" label="偏移量" width="80" />
        <el-table-column prop="site_title" label="SEO 标题" min-width="200" show-overflow-tooltip />
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.is_active" @change="toggleActive(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="edit(row)">编辑</el-button>
            <el-button size="small" type="success" @click="regen(row)">重生 nginx</el-button>
            <el-popconfirm title="确定删除？" @confirm="del(row)">
              <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="addDialog" :title="form.id ? '编辑站点' : '新建站点'" width="700px">
      <el-form :model="form" label-width="100px">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="域名"><el-input v-model="form.host" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="站名"><el-input v-model="form.name" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="主题">
          <el-select v-model="form.theme" style="width: 100%;" filterable>
            <el-option v-for="t in themes" :key="t.id" :label="`${t.name} (${t.code})`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="SEO 标题"><el-input v-model="form.site_title" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="SEO 关键词"><el-input v-model="form.site_keywords" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="SEO 描述"><el-input v-model="form.site_description" type="textarea" :rows="2" /></el-form-item>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="偏移量"><el-input-number v-model="form.offset" :min="0" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="GEO 语言"><el-input v-model="form.geo_lang" /></el-form-item></el-col>
        </el-row>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="GEO 地区"><el-input v-model="form.geo_region" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="Canonical"><el-input v-model="form.canonical_domain" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="Logo URL"><el-input v-model="form.logo" /></el-form-item>
        <el-form-item label="Favicon"><el-input v-model="form.favicon" /></el-form-item>
        <el-form-item label="robots.txt"><el-input v-model="form.robots_txt" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="Head 注入"><el-input v-model="form.head_inject" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="Body 注入"><el-input v-model="form.body_inject" type="textarea" :rows="3" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { siteApi } from '@/api/site'

const list = ref([])
const loading = ref(false)
const themes = ref([])
const addDialog = ref(false)
const filters = reactive({ q: '' })

const form = reactive({
  id: null, host: '', name: '', theme: null,
  site_title: '', site_description: '', site_keywords: '',
  logo: '', favicon: '', robots_txt: 'User-agent: *\nAllow: /\n',
  sitemap_enabled: true, geo_region: 'CN', geo_lang: 'zh-CN',
  canonical_domain: '', offset: 0, head_inject: '', body_inject: '', is_active: true,
})

async function loadData() {
  loading.value = true
  try {
    const { data } = await siteApi.list({ page_size: 100, ...filters })
    list.value = data.results || data
  } finally { loading.value = false }
}

async function loadThemes() {
  const { data } = await siteApi.listThemes()
  themes.value = data.results || data
}

async function toggleActive(row) {
  await siteApi.update(row.id, { is_active: !row.is_active })
  loadData()
}

function edit(row) {
  Object.assign(form, row)
  form.theme = row.theme
  addDialog.value = true
}

async function save() {
  if (form.id) {
    await siteApi.update(form.id, form)
  } else {
    await siteApi.create(form)
  }
  ElMessage.success('已保存')
  addDialog.value = false
  Object.assign(form, { id: null, host: '', name: '', site_title: '' })
  loadData()
}

async function regen(row) {
  await siteApi.regenerateNginx(row.id)
  ElMessage.success('已重新生成 nginx 配置')
}

async function del(row) {
  await siteApi.delete(row.id)
  ElMessage.success('已删除')
  loadData()
}

onMounted(() => {
  loadData()
  loadThemes()
})
</script>
