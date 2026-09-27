<template>
  <div class="page-container">
    <el-page-header :title="'返回'" @back="$router.push('/admin/tasks')" :content="task.name || '加载中'" />
    <el-row :gutter="16" class="mt-4">
      <el-col :span="16">
        <el-card shadow="never">
          <template #header>任务详情</template>
          <el-descriptions :column="2" border v-loading="loading">
            <el-descriptions-item label="状态"><el-tag :type="statusColor(task.status)" size="small">{{ statusMap[task.status] }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="模式">{{ modeMap[task.mode] }}</el-descriptions-item>
            <el-descriptions-item label="线程范围">{{ task.threads_min }} - {{ task.threads_max }}</el-descriptions-item>
            <el-descriptions-item label="间隔范围">{{ task.interval_min }} - {{ task.interval_max }} 秒</el-descriptions-item>
            <el-descriptions-item label="内容存储">{{ storageMap[task.content_storage] }}</el-descriptions-item>
            <el-descriptions-item label="封面格式">{{ task.cover_format }}</el-descriptions-item>
            <el-descriptions-item label="乱序重排"><el-tag size="small" :type="task.enable_disorder ? 'success' : 'info'">{{ task.enable_disorder ? '开' : '关' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="URL去重"><el-tag size="small" :type="task.enable_dedup_by_url ? 'success' : 'info'">{{ task.enable_dedup_by_url ? '开' : '关' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="标题去重"><el-tag size="small" :type="task.enable_dedup_by_title ? 'success' : 'info'">{{ task.enable_dedup_by_title ? '开' : '关' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="内容清洗"><el-tag size="small" :type="task.enable_cleaner ? 'success' : 'info'">{{ task.enable_cleaner ? '开' : '关' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="智能分类"><el-tag size="small" :type="task.enable_classifier ? 'success' : 'info'">{{ task.enable_classifier ? '开' : '关' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="完结检测"><el-tag size="small" :type="task.enable_finished_detection ? 'success' : 'info'">{{ task.enable_finished_detection ? '开' : '关' }}</el-tag></el-descriptions-item>
            <el-descriptions-item label="开始时间">{{ task.started_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="结束时间">{{ task.finished_at || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Celery ID">{{ task.celery_task_id || '-' }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ task.created_at }}</el-descriptions-item>
          </el-descriptions>

          <div class="mt-4">
            <h4>实时进度</h4>
            <el-progress :percentage="progressPct" :status="progressStatus" />
            <p>共 {{ progress.total }} 条，已处理 {{ progress.processed }}，成功 {{ progress.success }}，失败 {{ progress.failed }}，跳过 {{ progress.skipped }}</p>
          </div>

          <div class="mt-4 flex gap-3">
            <el-button v-if="task.status === 'draft' || task.status === 'done' || task.status === 'error' || task.status === 'stopped'"
              type="primary" @click="run">立即执行</el-button>
            <el-button v-if="task.status === 'running'" type="warning" @click="pause">暂停</el-button>
            <el-button v-if="task.status === 'running' || task.status === 'paused'" type="danger" @click="stop">停止</el-button>
          </div>
        </el-card>
      </el-col>

      <el-col :span="8">
        <el-card shadow="never">
          <template #header>运行中参数调整</template>
          <el-form label-width="100px" :model="params">
            <el-form-item label="最小线程"><el-input-number v-model="params.threads_min" :min="1" :max="20" style="width: 100%;" /></el-form-item>
            <el-form-item label="最大线程"><el-input-number v-model="params.threads_max" :min="1" :max="20" style="width: 100%;" /></el-form-item>
            <el-form-item label="最小间隔"><el-input-number v-model="params.interval_min" :min="0" :step="0.5" :precision="1" style="width: 100%;" /></el-form-item>
            <el-form-item label="最大间隔"><el-input-number v-model="params.interval_max" :min="0" :step="0.5" :precision="1" style="width: 100%;" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="updateParams">应用参数</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mt-4">
      <template #header>执行日志</template>
      <el-timeline>
        <el-timeline-item v-for="log in logs" :key="log.id"
          :type="log.level === 'error' ? 'danger' : log.level === 'warning' ? 'warning' : 'primary'"
          :timestamp="log.created_at">
          <p>{{ log.message }}</p>
          <p v-if="log.url" style="font-size: 12px; color: #909399;">URL: {{ log.url }}</p>
        </el-timeline-item>
        <el-empty v-if="!logs.length" description="暂无日志" />
      </el-timeline>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { taskApi } from '@/api/task'

const route = useRoute()
const taskId = route.params.id
const task = ref({})
const logs = ref([])
const loading = ref(false)
const progress = ref({ total: 0, processed: 0, success: 0, failed: 0, skipped: 0 })

const params = reactive({ threads_min: 2, threads_max: 5, interval_min: 1, interval_max: 3 })

const statusMap = { draft: '草稿', queued: '已入队', running: '运行中', paused: '已暂停', stopped: '已停止', done: '完成', error: '失败' }
const modeMap = { full: '完全覆盖', incremental: '增量更新' }
const storageMap = { db: '数据库', txt: 'TXT文件', both: '两者' }
const statusColorMap = { draft: 'info', queued: 'info', running: 'warning', paused: 'info', stopped: 'info', done: 'success', error: 'danger' }
const statusColor = (s) => statusColorMap[s] || 'info'

const progressPct = computed(() => progress.value.total ? Math.round(progress.value.processed / progress.value.total * 100) : 0)
const progressStatus = computed(() => {
  if (task.value.status === 'done') return 'success'
  if (task.value.status === 'error') return 'exception'
  return ''
})

async function loadTask() {
  loading.value = true
  try {
    const { data } = await taskApi.detail(taskId)
    task.value = data
    Object.assign(params, {
      threads_min: data.threads_min, threads_max: data.threads_max,
      interval_min: data.interval_min, interval_max: data.interval_max,
    })
    progress.value = {
      total: data.total_items, processed: data.processed_items,
      success: data.success_items, failed: data.failed_items, skipped: data.skipped_items,
    }
  } finally { loading.value = false }
}

async function loadLogs() {
  const { data } = await taskApi.logs(taskId)
  logs.value = data
}

async function loadProgress() {
  const { data } = await taskApi.progress(taskId)
  progress.value = data
}

async function run() {
  await taskApi.run(taskId)
  ElMessage.success('已入队')
  loadTask()
}

async function pause() {
  await taskApi.pause(taskId)
  ElMessage.success('已暂停')
  loadTask()
}

async function stop() {
  await taskApi.stop(taskId)
  ElMessage.success('已停止')
  loadTask()
}

async function updateParams() {
  await taskApi.updateParams(taskId, params)
  ElMessage.success('已应用')
  loadTask()
}

let timer
onMounted(() => {
  loadTask()
  loadLogs()
  timer = setInterval(() => {
    if (task.value.status === 'running') {
      loadProgress()
      loadLogs()
    }
  }, 3000)
})
onUnmounted(() => clearInterval(timer))
</script>
