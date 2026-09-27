<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>
        <div class="flex justify-between items-center">
          <span>SEO 检测面板</span>
          <div>
            <el-button @click="loadAudit" :loading="loading">刷新检测</el-button>
            <el-button type="primary" @click="regenSitemaps" :loading="regenLoading">重新生成 sitemap</el-button>
          </div>
        </div>
      </template>

      <el-alert title="SEO 检测会对每个站点的 TDK、GEO、canonical、robots、sitemap 等 12 项关键配置进行检查" type="info" :closable="false" class="mb-4" />

      <el-table :data="audits" v-loading="loading" stripe row-key="site_id">
        <el-table-column prop="site_host" label="站点" width="200" />
        <el-table-column label="综合评分" width="140">
          <template #default="{ row }">
            <el-progress :percentage="row.score" :color="scoreColor(row.score)" :stroke-width="14" text-inside />
          </template>
        </el-table-column>
        <el-table-column label="Errors" width="80" align="center">
          <template #default="{ row }">
            <el-badge :value="row.summary.errors" :type="row.summary.errors ? 'danger' : 'primary'" />
          </template>
        </el-table-column>
        <el-table-column label="Warnings" width="100" align="center">
          <template #default="{ row }">
            <el-badge :value="row.summary.warnings" :type="row.summary.warnings ? 'warning' : 'primary'" />
          </template>
        </el-table-column>
        <el-table-column label="OK" width="80" align="center">
          <template #default="{ row }">
            <el-badge :value="row.summary.oks" type="success" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="160" fixed="right">
          <template #default="{ row }">
            <el-button size="small" type="primary" plain @click="showDetail(row)">查看详情</el-button>
            <el-button size="small" @click="viewSitemap(row)">Sitemap</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="detailVisible" :title="`SEO 检测详情 - ${currentAudit?.site_host || ''}`" width="80%" top="5vh">
      <div v-if="currentAudit">
        <el-row :gutter="16" class="mb-4">
          <el-col :span="6">
            <el-card shadow="never" class="score-card">
              <p class="score-label">综合评分</p>
              <p class="score-value" :style="{color: scoreColor(currentAudit.score)}">{{ currentAudit.score }}</p>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <p class="count-label errors">Errors</p>
              <p class="count-value">{{ currentAudit.summary.errors }}</p>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <p class="count-label warnings">Warnings</p>
              <p class="count-value">{{ currentAudit.summary.warnings }}</p>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card shadow="never">
              <p class="count-label ok">OK 项</p>
              <p class="count-value">{{ currentAudit.summary.oks }}</p>
            </el-card>
          </el-col>
        </el-row>

        <el-table :data="currentAudit.checks" stripe>
          <el-table-column label="检查项" width="180">
            <template #default="{ row }">
              <code>{{ row.check }}</code>
            </template>
          </el-table-column>
          <el-table-column label="级别" width="100">
            <template #default="{ row }">
              <el-tag :type="severityType(row.severity)" size="small">{{ severityLabel(row.severity) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="message" label="状态" min-width="280" />
          <el-table-column prop="suggestion" label="建议" show-overflow-tooltip />
        </el-table>
      </div>
    </el-dialog>

    <el-dialog v-model="sitemapVisible" title="Sitemap Preview" width="90%" top="5vh">
      <iframe :src="currentSitemapUrl" style="width: 100%; height: 70vh; border: 0; background: #fff;" />
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { seoApi } from '@/api/seo'

const audits = ref([])
const loading = ref(false)
const regenLoading = ref(false)
const detailVisible = ref(false)
const currentAudit = ref(null)
const sitemapVisible = ref(false)
const currentSitemapUrl = ref('')

async function loadAudit() {
  loading.value = true
  try {
    const { data } = await seoApi.auditAll()
    audits.value = data.results || []
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function regenSitemaps() {
  regenLoading.value = true
  try {
    const { data } = await seoApi.regenSitemaps()
    ElMessage.success(`已生成 ${data.count} 个 sitemap`)
  } finally {
    regenLoading.value = false
  }
}

function showDetail(audit) {
  currentAudit.value = audit
  detailVisible.value = true
}

function viewSitemap(audit) {
  currentSitemapUrl.value = `/sitemap.xml`
  sitemapVisible.value = true
}

const scoreColor = (score) => {
  if (score >= 80) return '#67c23a'
  if (score >= 60) return '#e6a23c'
  return '#f56c6c'
}

const severityType = (s) => ({
  error: 'danger', warning: 'warning', info: 'info', ok: 'success'
}[s] || 'info')
const severityLabel = (s) => ({
  error: '错误', warning: '警告', info: '提示', ok: '正常'
}[s] || s)

onMounted(loadAudit)
</script>

<style scoped lang="scss">
.score-card { background: #f0f9eb; }
.score-label, .count-label {
  font-size: 13px; color: #909399; margin: 0 0 6px;
}
.count-label.errors { color: #f56c6c; }
.count-label.warnings { color: #e6a23c; }
.count-label.ok { color: #67c23a; }
.score-value, .count-value {
  font-size: 32px; font-weight: 700; margin: 0;
}
</style>
