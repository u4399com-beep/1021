<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-3">
          <el-input v-model="filters.q" placeholder="搜索规则名" clearable style="width: 240px;" @keyup.enter="loadData" />
          <el-select v-model="filters.target" placeholder="目标类型" clearable style="width: 140px;" @change="loadData">
            <el-option label="列表页" value="list" />
            <el-option label="书籍页" value="book" />
            <el-option label="章节目录" value="toc" />
            <el-option label="章节内容" value="chapter" />
          </el-select>
          <el-select v-model="filters.source" placeholder="采集源" clearable filterable style="width: 200px;" @change="loadData">
            <el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
          </el-select>
          <el-button type="primary" @click="loadData">搜索</el-button>
        </div>
        <div>
          <el-button type="primary" @click="$router.push('/admin/rules/new')">新建规则</el-button>
          <el-button @click="dialogSourceVisible = true">采集源管理</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column prop="id" label="#" width="60" />
        <el-table-column prop="name" label="名称" min-width="200" show-overflow-tooltip />
        <el-table-column label="目标" width="120">
          <template #default="{ row }">
            <el-tag size="small">{{ targetMap[row.target] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="source_name" label="采集源" width="160" />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="toggleEnabled(row)" />
          </template>
        </el-table-column>
        <el-table-column prop="last_test_at" label="最近测试" width="170" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/admin/rules/${row.id}/edit`)">编辑</el-button>
            <el-button size="small" type="success" @click="quickTest(row)">测试</el-button>
            <el-popconfirm title="确定删除？" @confirm="del(row)">
              <template #reference>
                <el-button size="small" type="danger" plain>删除</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-model:current-page="filters.page"
        v-model:page-size="filters.page_size"
        :total="total"
        layout="total, sizes, prev, pager, next, jumper"
        @size-change="loadData"
        @current-change="loadData"
        class="mt-4 justify-center flex"
      />
    </el-card>

    <el-dialog v-model="dialogSourceVisible" title="采集源管理" width="700px">
      <el-form :model="newSource" label-width="80px" inline>
        <el-form-item label="名称"><el-input v-model="newSource.name" /></el-form-item>
        <el-form-item label="域名"><el-input v-model="newSource.host" placeholder="example.com" /></el-form-item>
        <el-form-item><el-button type="primary" @click="addSource">添加</el-button></el-form-item>
      </el-form>
      <el-table :data="sources" max-height="400">
        <el-table-column prop="name" label="名称" width="180" />
        <el-table-column prop="host" label="域名" />
        <el-table-column prop="rules_count" label="规则数" width="80" />
        <el-table-column label="操作" width="120">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="toggleSource(row)" />
            <el-popconfirm title="删除？" @confirm="delSource(row)">
              <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { ruleApi } from '@/api/rule'

const router = useRouter()
const list = ref([])
const total = ref(0)
const loading = ref(false)
const sources = ref([])
const dialogSourceVisible = ref(false)

const filters = reactive({ page: 1, page_size: 20, q: '', target: '', source: '' })
const targetMap = { list: '列表页', book: '书籍页', toc: '章节目录', chapter: '章节内容' }

const newSource = reactive({ name: '', host: '' })

async function loadData() {
  loading.value = true
  try {
    const { data } = await ruleApi.list(filters)
    list.value = data.results || data
    total.value = data.count || list.value.length
  } finally { loading.value = false }
}

async function loadSources() {
  const { data } = await ruleApi.listSources({ page_size: 100 })
  sources.value = data.results || data
}

async function toggleEnabled(row) {
  try {
    if (row.enabled) await ruleApi.disable(row.id)
    else await ruleApi.enable(row.id)
    ElMessage.success('已更新')
    loadData()
  } catch (e) {}
}

async function quickTest(row) {
  router.push({ path: `/admin/rules/${row.id}/edit`, query: { test: 1 } })
}

async function del(row) {
  await ruleApi.delete(row.id)
  ElMessage.success('已删除')
  loadData()
}

async function addSource() {
  if (!newSource.name || !newSource.host) {
    ElMessage.warning('请填写名称和域名')
    return
  }
  await ruleApi.createSource({ ...newSource })
  newSource.name = ''; newSource.host = ''
  ElMessage.success('已添加')
  loadSources()
}

async function toggleSource(row) {
  await ruleApi.updateSource(row.id, { enabled: !row.enabled })
  loadSources()
}

async function delSource(row) {
  await ruleApi.deleteSource(row.id)
  ElMessage.success('已删除')
  loadSources()
}

onMounted(() => {
  loadData()
  loadSources()
})
</script>
