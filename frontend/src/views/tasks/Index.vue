<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-3">
          <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px;" @change="loadData">
            <el-option v-for="s in ['draft','queued','running','paused','stopped','done','error']" :key="s" :label="statusMap[s]" :value="s" />
          </el-select>
          <el-input v-model="filters.q" placeholder="搜索任务名" clearable style="width: 220px;" @keyup.enter="loadData" />
          <el-button type="primary" @click="loadData">搜索</el-button>
        </div>
        <el-button type="primary" @click="batchDialog = true">批量操作</el-button>
      </div>
      <el-table v-loading="loading" :data="list" stripe @selection-change="handleSelectionChange">
        <el-table-column type="selection" width="40" />
        <el-table-column prop="id" label="#" width="60" />
        <el-table-column prop="name" label="任务名" min-width="180" show-overflow-tooltip />
        <el-table-column label="状态" width="120">
          <template #default="{ row }"><el-tag :type="statusColor(row.status)" size="small">{{ statusMap[row.status] }}</el-tag></template>
        </el-table-column>
        <el-table-column label="模式" width="100"><template #default="{ row }">{{ modeMap[row.mode] }}</template></el-table-column>
        <el-table-column label="线程" width="80"><template #default="{ row }">{{ row.threads_min }}-{{ row.threads_max }}</template></el-table-column>
        <el-table-column label="进度" min-width="180">
          <template #default="{ row }">
            <el-progress :percentage="row.total_items ? Math.round(row.processed_items / row.total_items * 100) : 0" :status="row.status === 'done' ? 'success' : row.status === 'error' ? 'exception' : ''" />
            <span style="font-size: 12px; color: #909399;">{{ row.processed_items }}/{{ row.total_items }} 成功{{ row.success_items }} 失败{{ row.failed_items }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column prop="started_at" label="开始时间" width="160" />
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/admin/tasks/${row.id}`)">详情</el-button>
            <el-button v-if="['draft','done','error','stopped'].includes(row.status)" size="small" type="primary" @click="run(row)">执行</el-button>
            <el-button v-if="row.status === 'running'" size="small" type="warning" @click="pause(row)">暂停</el-button>
            <el-button v-if="['running','paused'].includes(row.status)" size="small" type="danger" @click="stop(row)">停止</el-button>
          </template>
        </el-table-column>
      </el-table>
      <el-pagination v-model:current-page="filters.page" v-model:page-size="filters.page_size" :total="total" layout="total, sizes, prev, pager, next, jumper" @size-change="loadData" @current-change="loadData" class="mt-4 justify-center flex" />
    </el-card>
    <el-dialog v-model="batchDialog" title="批量操作" width="500px">
      <p>已选 {{ selectedIds.length }} 个任务</p>
      <div class="flex gap-3 mt-4">
        <el-button type="primary" @click="batchRun" :disabled="!selectedIds.length">批量执行</el-button>
        <el-button type="warning" @click="batchPause" :disabled="!selectedIds.length">批量暂停</el-button>
        <el-button type="danger" @click="batchStop" :disabled="!selectedIds.length">批量停止</el-button>
      </div>
    </el-dialog>
  </div>
</template>
<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { taskApi } from '@/api/task'
const list = ref([]); const total = ref(0); const loading = ref(false)
const filters = reactive({ page: 1, page_size: 20, status: '', q: '' })
const statusMap = { draft:'草稿', queued:'已入队', running:'运行中', paused:'已暂停', stopped:'已停止', done:'完成', error:'失败' }
const modeMap = { full:'完全覆盖', incremental:'增量更新' }
const statusColorMap = { draft:'info', queued:'info', running:'warning', paused:'info', stopped:'info', done:'success', error:'danger' }
const statusColor = (s) => statusColorMap[s] || 'info'
const selectedIds = ref([]); const batchDialog = ref(false)
const handleSelectionChange = (rows) => { selectedIds.value = rows.map(r => r.id) }
async function loadData() { loading.value = true; try { const { data } = await taskApi.list(filters); list.value = data.results || data; total.value = data.count || list.value.length } finally { loading.value = false } }
async function run(row) { await taskApi.run(row.id); ElMessage.success('已入队'); setTimeout(loadData, 500) }
async function pause(row) { await taskApi.pause(row.id); ElMessage.success('已暂停'); loadData() }
async function stop(row) { await taskApi.stop(row.id); ElMessage.success('已停止'); loadData() }
async function batchRun() { await taskApi.batchRun(selectedIds.value); ElMessage.success('已批量执行'); batchDialog.value = false; loadData() }
async function batchPause() { await taskApi.batchPause(selectedIds.value); ElMessage.success('已批量暂停'); batchDialog.value = false; loadData() }
async function batchStop() { await taskApi.batchStop(selectedIds.value); ElMessage.success('已批量停止'); batchDialog.value = false; loadData() }
onMounted(loadData)
</script>
