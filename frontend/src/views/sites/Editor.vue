<template>
  <div class="page-container">
    <el-card shadow="never">
      <el-page-header title="返回" content="编辑站点" @back="$router.push('/admin/sites')" />
      <el-form :model="form" label-width="120px" class="mt-4">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="域名"><el-input v-model="form.host" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="站名"><el-input v-model="form.name" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="主题">
          <el-select v-model="form.theme" style="width: 100%;" filterable>
            <el-option v-for="t in themes" :key="t.id" :label="`${t.name} (${t.code})`" :value="t.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="SEO 标题"><el-input v-model="form.site_title" /></el-form-item>
        <el-form-item label="SEO 描述"><el-input v-model="form.site_description" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="SEO 关键词"><el-input v-model="form.site_keywords" /></el-form-item>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="偏移量"><el-input-number v-model="form.offset" :min="0" style="width: 100%;" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="GEO 语言"><el-input v-model="form.geo_lang" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="robots.txt"><el-input v-model="form.robots_txt" type="textarea" :rows="3" /></el-form-item>
        <el-form-item>
          <el-button type="primary" @click="save">保存</el-button>
          <el-button @click="$router.push('/admin/sites')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { siteApi } from '@/api/site'
const route = useRoute(); const router = useRouter()
const themes = ref([])
const form = reactive({ id: null, host: '', name: '', theme: null, site_title: '', site_description: '', site_keywords: '', robots_txt: 'User-agent: *\nAllow: /\n', sitemap_enabled: true, geo_region: 'CN', geo_lang: 'zh-CN', canonical_domain: '', offset: 0, head_inject: '', body_inject: '', is_active: true })
async function loadThemes() { const { data } = await siteApi.listThemes(); themes.value = data.results || data }
async function save() { if (form.id) { await siteApi.update(form.id, form) } else { await siteApi.create(form) }; ElMessage.success('已保存'); router.push('/admin/sites') }
onMounted(async () => { await loadThemes(); if (route.params.id) { const { data } = await siteApi.detail(route.params.id); Object.assign(form, data) } })
</script>
