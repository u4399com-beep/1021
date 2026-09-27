<template>
  <div class="page-container">
    <el-row :gutter="16">
      <el-col :span="14">
        <el-card shadow="never">
          <template #header>下载模板</template>
          <el-button type="primary" @click="addDialog = true" class="mb-4">新建模板</el-button>
          <el-table :data="templates" v-loading="loading" stripe>
            <el-table-column prop="name" label="名称" min-width="160" />
            <el-table-column label="格式" width="80"><template #default="{ row }">{{ row.output_format.toUpperCase() }}</template></el-table-column>
            <el-table-column label="混淆" width="80"><template #default="{ row }"><el-tag size="small" :type="row.enable_confusion ? 'success' : 'info'">{{ row.enable_confusion ? '开' : '关' }}</el-tag></template></el-table-column>
            <el-table-column label="启用" width="80"><template #default="{ row }"><el-switch :model-value="row.enabled" @change="toggleTemplate(row)" /></template></el-table-column>
            <el-table-column label="操作" width="120"><template #default="{ row }"><el-button size="small" @click="edit(row)">编辑</el-button></template></el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card shadow="never">
          <template #header>下载记录</template>
          <el-table :data="records" v-loading="loadingRecords" max-height="600">
            <el-table-column prop="book_title" label="书名" min-width="160" show-overflow-tooltip />
            <el-table-column label="格式" width="80"><template #default="{ row }">{{ row.output_format.toUpperCase() }}</template></el-table-column>
            <el-table-column label="大小" width="100"><template #default="{ row }">{{ (row.file_size / 1024).toFixed(1) }} KB</template></el-table-column>
            <el-table-column prop="chapters_count" label="章节" width="80" />
            <el-table-column prop="created_at" label="时间" width="160" />
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button size="small" type="primary" plain @click="download(row)">下载</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>
    </el-row>

    <el-dialog v-model="addDialog" :title="form.id ? '编辑模板' : '新建模板'" width="700px">
      <el-form :model="form" label-width="120px">
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="名称"><el-input v-model="form.name" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="输出格式">
            <el-select v-model="form.output_format" style="width: 100%;">
              <el-option label="TXT" value="txt" />
              <el-option label="EPUB" value="epub" />
            </el-select>
          </el-form-item></el-col>
        </el-row>
        <el-form-item label="章节头部"><el-input v-model="form.chapter_header" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="章节尾部"><el-input v-model="form.chapter_footer" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="前言"><el-input v-model="form.book_preface" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="后记"><el-input v-model="form.book_afterword" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="站点信息块"><el-input v-model="form.site_info_block" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="广告块"><el-input v-model="form.ad_block" type="textarea" :rows="3" /></el-form-item>
        <el-row :gutter="20">
          <el-col :span="12"><el-form-item label="启用混淆"><el-switch v-model="form.enable_confusion" /></el-form-item></el-col>
          <el-col :span="12"><el-form-item label="混淆密度"><el-input-number v-model="form.confusion_density" :step="0.005" :min="0" :max="0.05" :precision="3" /></el-form-item></el-col>
        </el-row>
        <el-form-item label="混淆字符集"><el-input v-model="form.confusion_chars" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { downloadApi } from '@/api/system'

const templates = ref([])
const records = ref([])
const loading = ref(false)
const loadingRecords = ref(false)
const addDialog = ref(false)

const form = reactive({
  id: null, name: '', output_format: 'txt',
  chapter_header: '', chapter_footer: '', book_preface: '', book_afterword: '',
  site_info_block: '', ad_block: '',
  enable_confusion: false, confusion_density: 0.005,
  confusion_chars: '\u200b\u200c\u200d\ufeff', enabled: true,
})

async function loadTemplates() {
  loading.value = true
  try {
    const { data } = await downloadApi.listTemplates({ page_size: 50 })
    templates.value = data.results || data
  } finally { loading.value = false }
}

async function loadRecords() {
  loadingRecords.value = true
  try {
    const { data } = await downloadApi.listRecords({ page_size: 50 })
    records.value = data.results || data
  } finally { loadingRecords.value = false }
}

function edit(row) {
  Object.assign(form, row)
  addDialog.value = true
}

async function save() {
  if (form.id) {
    await downloadApi.updateTemplate(form.id, form)
  } else {
    delete form.id
    await downloadApi.createTemplate({ ...form })
  }
  ElMessage.success('已保存')
  addDialog.value = false
  Object.assign(form, { id: null, name: '' })
  loadTemplates()
}

async function toggleTemplate(row) {
  await downloadApi.updateTemplate(row.id, { enabled: !row.enabled })
  loadTemplates()
}

function download(row) {
  window.open(`/api/v1/downloads/records/${row.id}/download/`, '_blank')
}

onMounted(() => {
  loadTemplates()
  loadRecords()
})
</script>
