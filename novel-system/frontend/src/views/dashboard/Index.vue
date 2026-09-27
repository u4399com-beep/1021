<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="6" v-for="card in stats" :key="card.key">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-body">
            <el-icon :size="32" :color="card.color"><component :is="card.icon" /></el-icon>
            <div>
              <div class="stat-label">{{ card.label }}</div>
              <div class="stat-value">{{ card.value }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt-4">
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>书籍状态分布</template>
          <v-chart class="chart" :option="statusChartOption" autoresize v-if="statusChartOption" />
          <el-empty v-else />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card shadow="never">
          <template #header>Top 10 采集源</template>
          <v-chart class="chart" :option="sourceChartOption" autoresize v-if="sourceChartOption" />
          <el-empty v-else />
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16" class="mt-4">
      <el-col :span="24">
        <el-card shadow="never">
          <template #header>系统信息</template>
          <el-descriptions :column="3" border>
            <el-descriptions-item label="Django 版本">{{ system.django || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Python 版本">{{ system.python || '-' }}</el-descriptions-item>
            <el-descriptions-item label="队列长度">{{ system.queue_len || 0 }}</el-descriptions-item>
            <el-descriptions-item label="运行中任务">{{ stats.find(s => s.key === 'running_tasks')?.value || 0 }}</el-descriptions-item>
            <el-descriptions-item label="站点数量">{{ stats.find(s => s.key === 'sites')?.value || 0 }}</el-descriptions-item>
            <el-descriptions-item label="书籍总数">{{ stats.find(s => s.key === 'books')?.value || 0 }}</el-descriptions-item>
          </el-descriptions>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import VChart from 'vue-echarts'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { PieChart, BarChart } from 'echarts/charts'
import { TitleComponent, TooltipComponent, GridComponent, LegendComponent } from 'echarts/components'
import http from '@/api'

use([CanvasRenderer, PieChart, BarChart, TitleComponent, TooltipComponent, GridComponent, LegendComponent])

const stats = ref([
  { key: 'books', label: '书籍总数', value: 0, icon: 'Reading', color: '#409eff' },
  { key: 'chapters', label: '章节数', value: 0, icon: 'Document', color: '#67c23a' },
  { key: 'tasks', label: '采集任务', value: 0, icon: 'List', color: '#e6a23c' },
  { key: 'running_tasks', label: '运行中', value: 0, icon: 'Loading', color: '#f56c6c' },
  { key: 'sites', label: '站点数', value: 0, icon: 'Connection', color: '#909399' },
])

const dashboard = ref({})
const system = ref({})

const statusChartOption = computed(() => {
  if (!dashboard.value.by_status?.length) return null
  return {
    tooltip: { trigger: 'item' },
    legend: { bottom: 0 },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      data: dashboard.value.by_status.map(s => ({ name: s.status, value: s.count })),
    }],
  }
})

const sourceChartOption = computed(() => {
  if (!dashboard.value.by_source?.length) return null
  return {
    tooltip: { trigger: 'axis' },
    xAxis: { type: 'category', data: dashboard.value.by_source.map(s => s.source_site) },
    yAxis: { type: 'value' },
    series: [{ type: 'bar', data: dashboard.value.by_source.map(s => s.count), itemStyle: { color: '#409eff' } }],
    grid: { left: '3%', right: '4%', bottom: '3%', top: '5%', containLabel: true },
  }
})

async function loadData() {
  try {
    const { data } = await http.get('/dashboard/')
    dashboard.value = data
    stats.value.forEach(s => s.value = data[s.key] || 0)
  } catch (e) { console.error(e) }
  try {
    const { data } = await http.get('/system/')
    system.value = data
  } catch (e) {}
}

onMounted(loadData)
</script>

<style scoped lang="scss">
.stat-card .stat-body { display: flex; align-items: center; gap: 16px; }
.stat-card .stat-label { font-size: 12px; color: #909399; }
.stat-card .stat-value { font-size: 24px; font-weight: 600; color: #303133; }
.chart { height: 280px; }
</style>
