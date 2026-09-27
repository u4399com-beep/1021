<template>
  <div class="rule-editor page-container">
    <el-page-header :title="'返回'" @back="$router.push('/admin/rules')" :content="form.id ? `编辑规则 #${form.id}` : '新建规则'" />

    <el-card shadow="never" class="mt-4">
      <el-form :model="form" label-width="100px" :rules="rules" ref="formRef">
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="规则名" prop="name">
              <el-input v-model="form.name" placeholder="例如：起点-列表页" />
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="目标类型" prop="target">
              <el-select v-model="form.target" style="width: 100%;">
                <el-option label="列表页" value="list" />
                <el-option label="书籍信息页" value="book" />
                <el-option label="章节目录页" value="toc" />
                <el-option label="章节内容页" value="chapter" />
              </el-select>
            </el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="采集源">
              <el-select v-model="form.source" clearable filterable style="width: 100%;">
                <el-option v-for="s in sources" :key="s.id" :label="s.name" :value="s.id" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <el-col :span="6">
            <el-form-item label="优先级"><el-input-number v-model="form.priority" :min="0" :max="999" /></el-form-item>
          </el-col>
          <el-col :span="6">
            <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
          </el-col>
        </el-row>

        <el-divider content-position="left">规则配置 (JSON)</el-divider>

        <div class="config-editor mb-4">
          <vue-monaco-editor
            v-model="configJson"
            language="json"
            theme="vs-dark"
            :options="{ minimap: { enabled: false }, fontSize: 13, tabSize: 2, automaticLayout: true }"
            height="320"
          />
        </div>

        <el-alert :title="hintText" type="info" :closable="false" class="mb-4" />

        <el-divider content-position="left">测试</el-divider>

        <el-form-item label="测试 URL">
          <el-input v-model="testUrl" placeholder="https://www.example.com/list/1.html" clearable style="width: 500px;" />
          <el-button type="primary" :loading="testing" @click="runTest" class="ml-2">测试</el-button>
          <el-button @click="testDialogVisible = true; testHtml = ''">手动粘贴 HTML</el-button>
        </el-form-item>

        <el-form-item v-if="testResult">
          <div class="test-result">
            <div class="result-meta">
              <span>HTML 大小: {{ testResult.html_size }} bytes</span>
              <span v-if="testResult.elapsed_ms">耗时: {{ testResult.elapsed_ms }} ms</span>
              <el-tag :type="testResult.ok ? 'success' : 'danger'" size="small">{{ testResult.ok ? '成功' : '失败' }}</el-tag>
            </div>
            <pre class="result-body">{{ JSON.stringify(testResult.result, null, 2) }}</pre>
          </div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">保存</el-button>
          <el-button @click="$router.push('/admin/rules')">取消</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <el-dialog v-model="testDialogVisible" title="粘贴 HTML 进行测试" width="80%">
      <el-input v-model="testHtml" type="textarea" :rows="12" placeholder="把要测试的 HTML 粘贴到这里" />
      <template #footer>
        <el-button @click="testDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="testing" @click="runTestWithHtml">使用此 HTML 测试</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { VueMonacoEditor } from '@guolao/vue-monaco-editor'
import { ruleApi } from '@/api/rule'

const route = useRoute()
const router = useRouter()
const formRef = ref(null)

const isEdit = computed(() => !!route.params.id)
const form = reactive({
  id: null, name: '', target: 'list', source: null,
  priority: 100, enabled: true,
})
const configJson = ref(`{
  "item_selector": { "type": "css", "expr": "ul.book-list li" },
  "book_url":     { "type": "xpath", "expr": ".//a/@href" },
  "book_title":   { "type": "css", "expr": "h3.title::text" },
  "book_author":  { "type": "css", "expr": "span.author::text" }
}`)
const rules = {
  name: [{ required: true, message: '请填写规则名', trigger: 'blur' }],
  target: [{ required: true, message: '请选择目标类型', trigger: 'change' }],
}

const sources = ref([])
const testUrl = ref('')
const testHtml = ref('')
const testDialogVisible = ref(false)
const testResult = ref(null)
const testing = ref(false)
const saving = ref(false)

const hintText = computed(() => {
  const t = form.target
  if (t === 'list') return '字段: item_selector (顶层), book_url, book_title, book_author, book_cover, next_page'
  if (t === 'book') return '字段: title, author, cover, intro, category (multi), keywords (multi), status, last_chapter_title, toc_url'
  if (t === 'toc') return '字段: item_selector, chapter_url, chapter_title, next_page (分页)'
  if (t === 'chapter') return '字段: title, content, next_page (章节内容分页)'
  return ''
})

async function load() {
  if (!isEdit.value) return
  const { data } = await ruleApi.detail(route.params.id)
  Object.assign(form, data)
  configJson.value = JSON.stringify(data.config, null, 2)
  if (route.query.test && data.last_test_html) {
    testHtml.value = data.last_test_html
    testDialogVisible.value = true
  }
}

async function loadSources() {
  const { data } = await ruleApi.listSources({ page_size: 100 })
  sources.value = data.results || data
}

function parseConfig() {
  try {
    return JSON.parse(configJson.value)
  } catch (e) {
    ElMessage.error('JSON 格式错误: ' + e.message)
    return null
  }
}

async function save() {
  if (!formRef.value) return
  await formRef.value.validate()
  const cfg = parseConfig()
  if (!cfg) return
  saving.value = true
  try {
    const payload = { ...form, config: cfg, source: form.source || null }
    if (isEdit.value) {
      await ruleApi.update(form.id, payload)
    } else {
      delete payload.id
      await ruleApi.create(payload)
    }
    ElMessage.success('保存成功')
    router.push('/admin/rules')
  } finally {
    saving.value = false
  }
}

async function runTest() {
  if (!testUrl.value) {
    ElMessage.warning('请填写测试 URL')
    return
  }
  await _doTest({ target: form.target, config: parseConfig(), test_url: testUrl.value, rule_id: form.id })
}

async function runTestWithHtml() {
  if (!testHtml.value) {
    ElMessage.warning('请粘贴 HTML')
    return
  }
  await _doTest({
    target: form.target,
    config: parseConfig(),
    test_html: testHtml.value,
    rule_id: form.id,
  })
  testDialogVisible.value = false
}

async function _doTest(payload) {
  testing.value = true
  try {
    const { data } = await ruleApi.test(payload)
    testResult.value = data
    if (!data.ok) ElMessage.error('测试失败：' + (data.error || ''))
  } catch (e) {
    testResult.value = { ok: false, error: e.response?.data?.error || String(e) }
  } finally {
    testing.value = false
  }
}

onMounted(() => {
  loadSources()
  load()
})
</script>

<style scoped lang="scss">
.rule-editor .config-editor {
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  overflow: hidden;
}

.test-result {
  width: 100%;
  border: 1px solid #dcdfe6;
  border-radius: 8px;
  padding: 12px;
  background: #fafafa;

  .result-meta { display: flex; gap: 16px; align-items: center; margin-bottom: 8px; font-size: 13px; color: #606266; }
  .result-body {
    background: #1e1e1e; color: #d4d4d4; padding: 12px;
    border-radius: 4px; max-height: 360px; overflow-y: auto;
    font-family: 'JetBrains Mono', Menlo, monospace; font-size: 12px;
  }
}
</style>
