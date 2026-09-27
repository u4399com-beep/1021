<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>系统设置</template>
      <el-tabs v-model="tab">
        <el-tab-pane label="搜索引擎建议词" name="suggest">
          <el-form label-width="100px" inline>
            <el-form-item label="关键词">
              <el-input v-model="suggestKw" placeholder="例如：斗破苍穹" style="width: 280px;" @keyup.enter="searchSuggest" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="searchSuggest">拉取建议词</el-button>
            </el-form-item>
          </el-form>
          <el-row :gutter="16" v-if="suggestResult">
            <el-col :span="6" v-for="(items, engine) in suggestResult" :key="engine">
              <el-card shadow="hover">
                <template #header>{{ engine }}</template>
                <ul style="list-style: none; padding-left: 0;">
                  <li v-for="(s, idx) in items" :key="idx" style="padding: 6px 0; border-bottom: 1px dashed #ebeef5;">{{ s }}</li>
                </ul>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="采集引擎信息" name="crawler">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Firecrawl">已配置 API Key: {{ hasFirecrawl ? '是' : '否' }}</el-descriptions-item>
            <el-descriptions-item label="Browser Use">已配置 API Key: {{ hasBrowserUse ? '是' : '否' }}</el-descriptions-item>
            <el-descriptions-item label="Hyperbrowser">已配置 API Key: {{ hasHyperbrowser ? '是' : '否' }}</el-descriptions-item>
            <el-descriptions-item label="Playwright">已安装</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>

        <el-tab-pane label="系统信息" name="system">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Django">v{{ sys.django || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Python">{{ sys.python || '-' }}</el-descriptions-item>
            <el-descriptions-item label="队列长度">{{ sys.queue_len || 0 }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import http from '@/api'
import { suggestApi } from '@/api/system'

const tab = ref('suggest')
const suggestKw = ref('')
const suggestResult = ref(null)
const sys = ref({})

const hasFirecrawl = ref(false)
const hasBrowserUse = ref(false)
const hasHyperbrowser = ref(false)

async function searchSuggest() {
  if (!suggestKw.value) return
  const { data } = await suggestApi.get({ kw: suggestKw.value })
  suggestResult.value = data.suggestions
}

async function loadSys() {
  try {
    const { data } = await http.get('/system/')
    sys.value = data
  } catch (e) {}
}

onMounted(loadSys)
</script>
