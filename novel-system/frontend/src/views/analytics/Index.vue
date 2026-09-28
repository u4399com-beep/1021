<template>
  <div class="page-container">
    <!-- 系统健康度卡片 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :span="6" v-for="card in healthCards" :key="card.key">
        <el-card shadow="hover" :class="['health-card', card.level]">
          <div class="flex items-center justify-between">
            <div>
              <p class="health-label">{{ card.label }}</p>
              <p class="health-value">{{ card.value }}{{ card.unit }}</p>
            </div>
            <el-icon :size="32" :color="card.color">
              <component :is="card.icon" />
            </el-icon>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 时间段选择 -->
    <el-card shadow="never" class="mb-4">
      <div class="flex justify-between items-center">
        <span>时间段：</span>
        <el-radio-group v-model="period" @change="loadAll">
          <el-radio-button label="week">最近7天</el-radio-button>
          <el-radio-button label="month">最近30天</el-radio-button>
          <el-radio-button label="quarter">最近90天</el-radio-button>
          <el-radio-button label="year">最近1年</el-radio-button>
        </el-radio-group>
      </div>
    </el-card>

    <!-- 图表区 -->
    <el-row :gutter="16" class="mb-4">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>新增书籍趋势</template>
          <v-chart class="chart" :option="booksChartOption" autoresize v-if="booksChartOption" />
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>任务完成情况</template>
          <v-chart class="chart" :option="tasksChartOption" autoresize v-if="tasksChartOption" />
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mb-4">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>采集成功率趋势</template>
          <v-chart class="chart" :option="rateChartOption" autoresize v-if="rateChartOption" />
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>Top 10 书籍（按浏览量）</template>
          <v-chart class="chart" :option="topBooksChartOption" autoresize v-if="topBooksChartOption" />
          <el-empty v-else description="暂无数据" />
        </el-card>
      </el-col>
    </el-row>

    <!-- 存储用量 -->
    <el-card shadow="never" class="mb-4">
      <template #header>存储用量</template>
      <el-descriptions :column="4" border v-loading="loadingStorage">
        <el-descriptions-item label="总用量">{{ storage.total_mb || 0 }} MB</el-descriptions-item>
        <el-descriptions-item label="封面图">{{ storage.breakdown?.covers?.mb || 0 }} MB</el-descriptions-item>
        <el-descriptions-item label="章节TXT">{{ storage.breakdown?.chapters?.mb || 0 }} MB</el-descriptions-item>
        <el-descriptions-item label="下载文件">{{ storage.breakdown?.downloads?.mb || 0 }} MB</el-descriptions-item>
      </el-descriptions>
    </el-card>

    <!-- 告警列表 -->
    <el-card shadow="never" v-if="alerts.length" class="mb-4">
      <template #header>
        <span style="color: #f56c6c;">系统告警 ({{ alerts.length }})</span>
      </template>
      <el-table :data="alerts" stripe>
        <el-table-column prop="level" label="级别" width="100">
          <template #default="{ row }">
            <el-tag :type="row.level === 'danger' ? 'danger' : 'warning'" size="small">
              {{ row.level === 'danger' ? '严重' : '警告' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="metric" label="指标" width="150" />
        <el-table-column prop="message" label="告警内容" />
        <el-table-column label="当前值" width="120">
          <template #default="{ row }">{{ row.value }}{{ row.metric === 'cpu' || row.metric === 'memory' || row.metric === 'disk' ? '%' : '' }}</template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, LineChart, PieChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import { dashboardAnalyticsApi } from '@/api/dashboard'

use([CanvasRenderer, BarChart, LineChart, PieChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent])

const period = ref('month')
const loadingStorage = ref(false)

const health = ref({})
const alerts = ref([])
const storage = ref({})
const booksData = ref(null)
const tasksData = ref(null)
const rateData = ref(null)
const topBooksData = ref(null)

const healthCards = computed(() => [
  { key: 'cpu', label: 'CPU', value: health.value.cpu_percent || 0, unit: '%', icon: 'Cpu', level: (health.value.cpu_percent || 0) > 80 ? 'danger' : 'ok', color: '#409eff' },
  { key: 'memory', label: '内存', value: health.value.memory?.percent || 0, unit: '%', icon: 'Monitor', level: (health.value.memory?.percent || 0) > 80 ? 'danger' : 'ok', color: '#67c23a' },
  { key: 'disk', label: '磁盘', value: health.value.disk?.percent || 0, unit: '%', icon: 'Coin', level: (health.value.disk?.percent || 0) > 80 ? 'danger' : 'ok', color: '#e6a23c' },
  { key: 'queue', label: '任务队列', value: (health.value.queue?.queued || 0) + (health.value.queue?.running || 0), unit: '', icon: 'List', level: 'info', color: '#909399' },
])

const booksChartOption = computed(() => {
  if (!booksData.value) return null
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: booksData.value.labels },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: booksData.value.datasets[0].data, itemStyle: { color: '#409eff' } }],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
  }
})

const tasksChartOption = computed(() => {
  if (!tasksData.value) return null
  return {
    tooltip: { trigger: 'axis' },
    legend: { bottom: 0 },
    xAxis: { type: 'category', data: tasksData.value.labels },
    yAxis: { type: 'value' },
    series: tasksData.value.datasets.map(d => ({ type: 'bar', name: d.label, data: d.data, itemStyle: { color: d.backgroundColor } })),
    grid: { left: '3%', right: '4%', bottom: '15%', top: '5%', containLabel: true },
  }
})

const rateChartOption = computed(() => {
  if (!rateData.value) return null
  return {
    tooltip: { trigger: 'axis', formatter: '{b}: {c}%' },
    xAxis: { type: 'category', data: rateData.value.labels },
    yAxis: { type: 'value', max: 100, axisLabel: { formatter: '{value}%' } },
    series: [{ type: 'line', data: rateData.value.datasets[0].data, smooth: true, itemStyle: { color: '#67c23a' }, areaStyle: { opacity: 0.2 } }],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '10%', containLabel: true },
  }
})

const topBooksChartOption = computed(() => {
  if (!topBooksData.value) return null
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'value' },
    yAxis: { type: 'category', data: topBooksData.value.labels, inverse: true },
    series: [{ type: 'bar', data: topBooksData.value.datasets[0].data, itemStyle: { color: '#e6a23c' } }],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
  }
})

async function loadHealth() {
  try {
    const { data } = await dashboardAnalyticsApi.health()
    health.value = data
    alerts.value = data.alerts || []
  } catch (e) { console.error(e) }
}

async function loadBooks() {
  try {
    const { data } = await dashboardAnalyticsApi.booksAdded({ period: period.value })
    booksData.value = data
  } catch (e) {}
}

async function loadTasks() {
  try {
    const { data } = await dashboardAnalyticsApi.tasksCompleted({ period: period.value })
    tasksData.value = data
  } catch (e) {}
}

async function loadRate() {
  try {
    const { data } = await dashboardAnalyticsApi.successRate({ period: period.value })
    rateData.value = data
  } catch (e) {}
}

async function loadTopBooks() {
  try {
    const { data } = await dashboardAnalyticsApi.topBooks({ metric: 'views', limit: 10 })
    topBooksData.value = data
  } catch (e) {}
}

async function loadStorage() {
  loadingStorage.value = true
  try {
    const { data } = await dashboardAnalyticsApi.storage()
    storage.value = data
  } finally { loadingStorage.value = false }
}

async function loadAll() {
  await Promise.all([loadBooks(), loadTasks(), loadRate(), loadTopBooks()])
}

let timer
onMounted(() => {
  loadHealth()
  loadAll()
  loadStorage()
  timer = setInterval(loadHealth, 30000)
})
onUnmounted(() => clearInterval(timer))
</script>

<style scoped lang="scss">
.health-card { margin-bottom: 0; }
.health-card.danger { border-left: 4px solid #f56c6c; }
.health-card.warning { border-left: 4px solid #e6a23c; }
.health-card.ok { border-left: 4px solid #67c23a; }
.health-card.info { border-left: 4px solid #909399; }
.health-label { font-size: 12px; color: #909399; margin: 0; }
.health-value { font-size: 24px; font-weight: 700; margin: 4px 0 0; color: #303133; }
.chart { height: 280px; }
.mb-4 { margin-bottom: 16px; }
</style>
