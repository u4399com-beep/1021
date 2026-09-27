<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>清洗规则</template>
      <el-button type="primary" @click="addDialog = true" class="mb-4">新建规则</el-button>
      <el-table :data="rules" v-loading="loading" stripe>
        <el-table-column prop="name" label="名称" min-width="180" />
        <el-table-column label="目标" width="120">
          <template #default="{ row }">{{ targetMap[row.target] }}</template>
        </el-table-column>
        <el-table-column label="策略" width="140">
          <template #default="{ row }">{{ strategyMap[row.strategy] }}</template>
        </el-table-column>
        <el-table-column prop="pattern" label="模式" show-overflow-tooltip min-width="280" />
        <el-table-column prop="priority" label="优先级" width="80" />
        <el-table-column label="启用" width="80">
          <template #default="{ row }">
            <el-switch :model-value="row.enabled" @change="toggle(row, $event)" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="200" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="test(row)">试清洗</el-button>
            <el-popconfirm title="确定删除？" @confirm="del(row)">
              <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
            </el-popconfirm>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <el-dialog v-model="addDialog" title="新建清洗规则" width="600px">
      <el-form :model="form" label-width="100px">
        <el-form-item label="名称"><el-input v-model="form.name" /></el-form-item>
        <el-form-item label="目标">
          <el-select v-model="form.target" style="width: 100%;">
            <el-option label="章节正文" value="chapter" />
            <el-option label="书籍简介" value="book" />
            <el-option label="作者简介" value="author" />
            <el-option label="全部" value="all" />
          </el-select>
        </el-form-item>
        <el-form-item label="策略">
          <el-select v-model="form.strategy" style="width: 100%;">
            <el-option label="正则替换" value="regex" />
            <el-option label="CSS 移除" value="css_remove" />
            <el-option label="XPath 移除" value="xpath_remove" />
            <el-option label="字符串移除" value="string_remove" />
            <el-option label="字符串替换" value="string_replace" />
          </el-select>
        </el-form-item>
        <el-form-item label="模式"><el-input v-model="form.pattern" type="textarea" :rows="3" /></el-form-item>
        <el-form-item label="替换为"><el-input v-model="form.replacement" type="textarea" :rows="2" /></el-form-item>
        <el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="addDialog = false">取消</el-button>
        <el-button type="primary" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="testDialog" title="试清洗" width="80%">
      <el-input v-model="testHtml" type="textarea" :rows="8" placeholder="粘贴要清洗的 HTML" />
      <el-button type="primary" @click="runTest" class="mt-4">执行清洗</el-button>
      <el-divider />
      <div v-if="testResult">
        <p>清洗前: {{ testResult.before_size }} 字节 → 清洗后: {{ testResult.after_size }} 字节</p>
        <pre style="background: #1e1e1e; color: #d4d4d4; padding: 12px; border-radius: 4px; max-height: 400px; overflow: auto; font-size: 12px;">{{ testResult.cleaned }}</pre>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { cleanerApi } from '@/api/system'

const rules = ref([])
const loading = ref(false)
const addDialog = ref(false)
const testDialog = ref(false)
const form = reactive({ name: '', target: 'chapter', strategy: 'regex', pattern: '', replacement: '', priority: 100, enabled: true })
const testHtml = ref('')
const testResult = ref(null)

const targetMap = { chapter: '章节', book: '书籍', author: '作者', all: '全部' }
const strategyMap = { regex: '正则替换', css_remove: 'CSS移除', xpath_remove: 'XPath移除', string_remove: '字符串移除', string_replace: '字符串替换' }

async function load() {
  loading.value = true
  try {
    const { data } = await cleanerApi.listRules({ page_size: 100 })
    rules.value = data.results || data
  } finally { loading.value = false }
}

async function save() {
  await cleanerApi.createRule({ ...form })
  ElMessage.success('已保存')
  addDialog.value = false
  Object.assign(form, { name: '', pattern: '', replacement: '' })
  load()
}

async function toggle(row, val) {
  await cleanerApi.updateRule(row.id, { enabled: val })
  load()
}

async function del(row) {
  await cleanerApi.deleteRule(row.id)
  ElMessage.success('已删除')
  load()
}

async function test(row) {
  testDialog.value = true
  testResult.value = null
}

async function runTest() {
  const { data } = await cleanerApi.preview({ html: testHtml.value, target: 'chapter' })
  testResult.value = data
}

onMounted(load)
</script>
