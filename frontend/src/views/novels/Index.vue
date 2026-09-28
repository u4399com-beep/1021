<template>
  <div class="page-container">
    <el-card shadow="never">
      <div class="flex justify-between items-center mb-4">
        <div class="flex items-center gap-3">
          <el-input v-model="filters.q" placeholder="搜索书名/简介/标签" clearable style="width: 280px;" @keyup.enter="loadData" />
          <el-select v-model="filters.status" placeholder="状态" clearable style="width: 140px;" @change="loadData">
            <el-option label="连载中" value="ongoing" />
            <el-option label="已完结" value="completed" />
            <el-option label="未知" value="unknown" />
          </el-select>
          <el-select v-model="filters.category" placeholder="分类" clearable filterable style="width: 160px;" @change="loadData">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
          <el-button type="primary" @click="loadData">搜索</el-button>
        </div>
        <div>
          <el-button type="success" @click="$router.push('/admin/tasks')">新增采集</el-button>
        </div>
      </div>

      <el-table v-loading="loading" :data="list" stripe>
        <el-table-column label="封面" width="80">
          <template #default="{ row }">
            <el-image v-if="row.cover_url_full" :src="row.cover_url_full" style="width: 50px; height: 70px;" fit="cover" />
            <div v-else style="width: 50px; height: 70px; background: #f0f0f0; display: flex; align-items: center; justify-content: center; color: #c0c4cc;">无</div>
          </template>
        </el-table-column>
        <el-table-column prop="title" label="书名" min-width="200" show-overflow-tooltip />
        <el-table-column prop="author_name" label="作者" width="120" />
        <el-table-column label="分类" width="180">
          <template #default="{ row }">
            <el-tag v-for="c in row.categories" :key="c" size="small" type="info" effect="plain" style="margin-right: 4px;">{{ c }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'completed' ? 'success' : 'warning'" size="small">
              {{ statusMap[row.status] || row.status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="chapter_count" label="章节数" width="90" />
        <el-table-column prop="word_count" label="字数" width="100" />
        <el-table-column prop="rating" label="评分" width="80" />
        <el-table-column prop="view_count" label="浏览" width="80" />
        <el-table-column prop="updated_at" label="更新时间" width="170" />
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="$router.push(`/admin/novels/${row.id}`)">详情</el-button>
            <el-button size="small" type="primary" @click="republish(row)" v-if="!row.is_published">发布</el-button>
            <el-popconfirm title="确定下架吗？" @confirm="softDelete(row)">
              <template #reference>
                <el-button size="small" type="danger" plain>下架</el-button>
              </template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>

      <div class="flex justify-between items-center mt-4">
        <span class="text-c0">共 {{ total }} 条</span>
        <el-pagination
          v-model:current-page="filters.page"
          v-model:page-size="filters.page_size"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="sizes, prev, pager, next, jumper"
          @size-change="loadData"
          @current-change="loadData"
        />
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { novelApi } from '@/api/novel'

const list = ref([])
const total = ref(0)
const loading = ref(false)
const categories = ref([])

const filters = reactive({ page: 1, page_size: 20, q: '', status: '', category: '' })
const statusMap = { ongoing: '连载中', completed: '已完结', unknown: '未知' }

async function loadData() {
  loading.value = true
  try {
    const { data } = await novelApi.list(filters)
    list.value = data.results || data
    total.value = data.count || list.value.length
  } catch (e) {
    ElMessage.error('加载失败')
  } finally {
    loading.value = false
  }
}

async function loadCategories() {
  try {
    const { data } = await novelApi.listCategories({ page_size: 100 })
    categories.value = data.results || data
  } catch (e) {}
}

async function republish(row) {
  await novelApi.republish(row.id)
  ElMessage.success('已发布')
  loadData()
}

async function softDelete(row) {
  await novelApi.delete(row.id)
  ElMessage.success('已下架')
  loadData()
}

onMounted(() => {
  loadCategories()
  loadData()
})
</script>

<style scoped>
.text-c0 { color: #c0c4cc; }
</style>
