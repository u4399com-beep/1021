<template>
  <div class="page-container">
    <el-page-header :title="'返回'" @back="$router.push('/admin/novels')" :content="book.title || '加载中'" />
    <el-card shadow="never" class="mt-4" v-loading="loading">
      <el-row :gutter="24" v-if="book.id">
        <el-col :span="6">
          <el-image :src="book.cover?.url || book.cover_url" style="width: 100%; max-width: 200px;" fit="cover" />
        </el-col>
        <el-col :span="18">
          <h2>{{ book.title }}</h2>
          <el-descriptions :column="2" border>
            <el-descriptions-item label="作者">{{ book.author?.name || '-' }}</el-descriptions-item>
            <el-descriptions-item label="状态">{{ statusMap[book.status] || book.status }}</el-descriptions-item>
            <el-descriptions-item label="分类">
              <el-tag v-for="c in book.categories" :key="c.id" size="small" effect="plain" style="margin-right: 4px;">{{ c.name }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="标签">
              <el-tag v-for="t in book.tags" :key="t.id" size="small" type="info" effect="plain" style="margin-right: 4px;">{{ t.name }}</el-tag>
            </el-descriptions-item>
            <el-descriptions-item label="字数">{{ book.word_count }}</el-descriptions-item>
            <el-descriptions-item label="章节数">{{ book.chapter_count }}</el-descriptions-item>
            <el-descriptions-item label="评分">{{ book.rating }}</el-descriptions-item>
            <el-descriptions-item label="浏览量">{{ book.view_count }}</el-descriptions-item>
            <el-descriptions-item label="源站点">{{ book.source_site }}</el-descriptions-item>
            <el-descriptions-item label="源URL"><a :href="book.source_url" target="_blank">{{ book.source_url }}</a></el-descriptions-item>
          </el-descriptions>
          <h3 class="mt-4 mb-2">简介</h3>
          <p style="line-height: 1.8; color: #606266;">{{ book.intro || '-' }}</p>
        </el-col>
      </el-row>

      <el-divider />

      <h3 class="mb-4">章节列表 ({{ chapters.length }})</h3>
      <el-table :data="chapters" stripe max-height="600">
        <el-table-column prop="order_index" label="序号" width="80" />
        <el-table-column prop="title" label="标题" min-width="280" show-overflow-tooltip />
        <el-table-column prop="status" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.status === 'published' ? 'success' : 'info'" size="small">{{ statusMap[row.status] }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="word_count" label="字数" width="100" />
        <el-table-column prop="fetched_at" label="采集时间" width="170" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { novelApi } from '@/api/novel'

const route = useRoute()
const book = ref({})
const chapters = ref([])
const loading = ref(false)

const statusMap = {
  ongoing: '连载中', completed: '已完结', unknown: '未知',
  pending: '待采集', fetched: '已采集', cleaned: '已清洗', published: '已发布', error: '失败',
}

async function load() {
  loading.value = true
  try {
    const { data } = await novelApi.detail(route.params.id)
    book.value = data
    chapters.value = data.chapters || []
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
