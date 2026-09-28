<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>智能分类测试</template>
          <el-form label-width="80px">
            <el-form-item label="书名"><el-input v-model="testForm.title" /></el-form-item>
            <el-form-item label="简介"><el-input v-model="testForm.intro" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="章节片段"><el-input v-model="testForm.snippet" type="textarea" :rows="5" /></el-form-item>
            <el-form-item>
              <el-button type="primary" @click="testClassify">试分类</el-button>
              <el-button @click="testFinished">试完结判断</el-button>
            </el-form-item>
          </el-form>
          <el-divider />
          <div v-if="classifyResult">
            <h4>分类结果</h4>
            <el-tag v-for="c in classifyResult.categories" :key="c.name" size="large" effect="dark" class="mr-2 mb-2">
              {{ c.name }} ({{ (c.score * 100).toFixed(1) }}%)
            </el-tag>
          </div>
          <div v-if="finishedResult !== null">
            <h4>完结判断</h4>
            <el-tag :type="finishedResult.finished ? 'success' : 'warning'" size="large" effect="dark">
              {{ finishedResult.finished ? '已完结' : '连载中' }}
            </el-tag>
          </div>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>
            <div class="flex justify-between items-center">
              <span>分类关键词</span>
              <el-button type="primary" size="small" @click="kwDialog = true">添加</el-button>
            </div>
          </template>
          <el-table :data="keywords" max-height="500" v-loading="loading">
            <el-table-column prop="category_name" label="分类" width="100" />
            <el-table-column prop="keyword" label="关键词" />
            <el-table-column prop="weight" label="权重" width="80" />
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
                <el-button size="small" type="danger" plain @click="delKw(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never" class="mt-4">
      <template #header>完结规则</template>
      <el-table :data="patterns">
        <el-table-column prop="name" label="名称" width="180" />
        <el-table-column prop="pattern" label="正则" min-width="280" show-overflow-tooltip />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column prop="enabled" label="启用" width="80" />
      </el-table>
    </el-card>

    <el-dialog v-model="kwDialog" title="添加分类关键词" width="400px">
      <el-form label-width="80px">
        <el-form-item label="分类"><el-input v-model="kwForm.category_name" /></el-form-item>
        <el-form-item label="关键词"><el-input v-model="kwForm.keyword" /></el-form-item>
        <el-form-item label="权重"><el-input-number v-model="kwForm.weight" :step="0.5" :min="0.1" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="kwDialog = false">取消</el-button>
        <el-button type="primary" @click="saveKw">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { classifierApi } from '@/api/system'

const testForm = reactive({ title: '斗破苍穹', intro: '一招斗气，大陆分裂', snippet: '斗气化马' })
const classifyResult = ref(null)
const finishedResult = ref(null)
const keywords = ref([])
const patterns = ref([])
const loading = ref(false)
const kwDialog = ref(false)
const kwForm = reactive({ category_name: '', keyword: '', weight: 1.0 })

async function loadKeywords() {
  loading.value = true
  try {
    const { data } = await classifierApi.listKeywords({ page_size: 200 })
    keywords.value = data.results || data
  } finally { loading.value = false }
}

async function loadPatterns() {
  const { data } = await classifierApi.listPatterns({ page_size: 100 })
  patterns.value = data.results || data
}

async function testClassify() {
  const { data } = await classifierApi.testClassify(testForm)
  classifyResult.value = data
}

async function testFinished() {
  const { data } = await classifierApi.testFinished({
    title: testForm.title, intro: testForm.intro, last_chapter_title: '大结局',
  })
  finishedResult.value = data
}

async function saveKw() {
  await classifierApi.createKeyword(kwForm)
  ElMessage.success('已添加')
  kwDialog.value = false
  Object.assign(kwForm, { category_name: '', keyword: '', weight: 1.0 })
  loadKeywords()
}

async function delKw(row) {
  await classifierApi.deleteKeyword(row.id)
  ElMessage.success('已删除')
  loadKeywords()
}

onMounted(() => {
  loadKeywords()
  loadPatterns()
})
</script>
