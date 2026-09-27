<template>
  <div class="page-container">
    <el-card shadow="never">
      <template #header>系统设置</template>
      <el-tabs v-model="tab">
        <el-tab-pane label="采集引擎" name="engine">
          <!-- Engine diagnostics + per-tier test -->
          <el-row :gutter="16" class="mb-4">
            <el-col :span="24">
              <el-button type="primary" @click="loadStatus" :loading="loadingStatus">刷新引擎状态</el-button>
            </el-col>
          </el-row>
          <el-table :data="tiers" v-loading="loadingStatus" border>
            <el-table-column prop="name" label="Tier" width="160">
              <template #default="{ row }">
                <el-tag :type="tierColor(row)" size="large">{{ row.name }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="已安装" width="100">
              <template #default="{ row }">
                <el-tag :type="row.installed ? 'success' : 'danger'" size="small" effect="plain">
                  {{ row.installed ? '✓ 是' : '✗ 否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="已配置" width="100">
              <template #default="{ row }">
                <el-tag :type="row.configured ? 'success' : 'warning'" size="small" effect="plain">
                  {{ row.configured ? '✓ 是' : '✗ 否' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="error" label="备注" show-overflow-tooltip />
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" type="primary" @click="quickTest(row.name)">测试</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left">完整 fallback 链路测试</el-divider>

          <el-form label-width="120px" :model="testForm" inline>
            <el-form-item label="目标 URL">
              <el-input v-model="testForm.url" placeholder="https://example.com/list" style="width: 400px;" />
            </el-form-item>
            <el-form-item label="指定 Tier">
              <el-select v-model="testForm.tier" clearable style="width: 180px;">
                <el-option label="自动（按 fallback 顺序）" :value="null" />
                <el-option label="httpx" value="httpx" />
                <el-option label="firecrawl" value="firecrawl" />
                <el-option label="browser-use" value="browser-use" />
                <el-option label="playwright" value="playwright" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="testing" @click="runTest">单 Tier 测试</el-button>
              <el-button :loading="fetching" @click="runFetch">完整 fallback 测试</el-button>
            </el-form-item>
          </el-form>

          <el-card v-if="testResults" shadow="never" class="mt-4">
            <template #header>测试结果</template>
            <el-table :data="testResults.results" border size="small">
              <el-table-column prop="tier" label="Tier" width="140" />
              <el-table-column label="结果" width="100">
                <template #default="{ row }">
                  <el-tag :type="row.success ? 'success' : 'danger'" size="small">
                    {{ row.success ? '成功' : '失败' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="elapsed_ms" label="耗时(ms)" width="100" />
              <el-table-column prop="html_size" label="HTML大小" width="120" />
              <el-table-column prop="error" label="错误" show-overflow-tooltip />
            </el-table>
          </el-card>

          <el-card v-if="fetchResult" shadow="never" class="mt-4">
            <template #header>Fallback 链路结果</template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="URL">{{ fetchResult.url }}</el-descriptions-item>
              <el-descriptions-item label="HTML 大小">{{ fetchResult.html_size }} bytes</el-descriptions-item>
            </el-descriptions>
            <pre class="preview-box">{{ fetchResult.preview }}</pre>
          </el-card>
        </el-tab-pane>

        <el-tab-pane label="搜索引擎建议词" name="suggest">
          <el-form label-width="100px" inline>
            <el-form-item label="关键词">
              <el-input v-model="suggestKw" placeholder="例如：斗破苍穹" style="width: 280px;" @keyup.enter="searchSuggest" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="searchSuggest">拉取建议词</el-button>
            </el-form-item>
          </el-form>
          <el-row :gutter="16" v-if="suggestResult">
            <el-col :span="6" v-for="(items, engine) in suggestResult" :key="engine">
              <el-card shadow="hover">
                <template #header>{{ engine }}</template>
                <ul style="list-style: none; padding-left: 0;">
                  <li v-for="(s, idx) in items" :key="idx" style="padding: 6px 0; border-bottom: 1px dashed #ebeef5;">{{ s }}</li>
                </ul>
              </el-card>
            </el-col>
          </el-row>
        </el-tab-pane>

        <el-tab-pane label="系统信息" name="system">
          <el-descriptions :column="2" border>
            <el-descriptions-item label="Django">v{{ sys.django || '-' }}</el-descriptions-item>
            <el-descriptions-item label="Python">{{ sys.python || '-' }}</el-descriptions-item>
            <el-descriptions-item label="队列长度">{{ sys.queue_len || 0 }}</el-descriptions-item>
          </el-descriptions>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import http from '@/api'
import { suggestApi, engineApi } from '@/api/system'

const tab = ref('engine')
const suggestKw = ref('')
const suggestResult = ref(null)
const sys = ref({})

// Engine status
const tiers = ref([])
const loadingStatus = ref(false)

// Engine test
const testForm = reactive({ url: '', tier: null })
const testing = ref(false)
const testResults = ref(null)
const fetching = ref(false)
const fetchResult = ref(null)

async function loadStatus() {
  loadingStatus.value = true
  try {
    const { data } = await engineApi.status()
    tiers.value = Object.entries(data.tiers || {}).map(([name, info]) => ({
      name, ...info,
      error: info.error || (info.installed && info.configured ? '运行就绪' : '未安装或未配置'),
    }))
  } catch (e) {
    console.error(e)
  } finally {
    loadingStatus.value = false
  }
}

function tierColor(row) {
  if (row.installed && row.configured) return 'success'
  if (row.installed) return 'warning'
  return 'info'
}

async function quickTest(tierName) {
  testForm.tier = tierName
  await runTest()
}

async function runTest() {
  if (!testForm.url) {
    ElMessage.warning('请填写 URL')
    return
  }
  testing.value = true
  testResults.value = null
  try {
    const { data } = await engineApi.test({ url: testForm.url, tier: testForm.tier || undefined })
    testResults.value = data
  } catch (e) {
    ElMessage.error('测试失败')
  } finally {
    testing.value = false
  }
}

async function runFetch() {
  if (!testForm.url) {
    ElMessage.warning('请填写 URL')
    return
  }
  fetching.value = true
  fetchResult.value = null
  try {
    const { data } = await engineApi.fetch({ url: testForm.url })
    fetchResult.value = data
    ElMessage.success(`成功获取 ${data.html_size} bytes`)
  } catch (e) {
    ElMessage.error('Fallback 失败：' + (e.response?.data?.error || ''))
  } finally {
    fetching.value = false
  }
}

async function searchSuggest() {
  if (!suggestKw.value) return
  const { data } = await suggestApi.get({ kw: suggestKw.value })
  suggestResult.value = data.suggestions
}

async function loadSys() {
  try {
    const { data } = await http.get('/system/')
    sys.value = data
  } catch (e) {}
}

onMounted(() => {
  loadStatus()
  loadSys()
})
</script>

<style scoped lang="scss">
.preview-box {
  background: #1e1e1e; color: #d4d4d4;
  padding: 12px; border-radius: 4px;
  max-height: 360px; overflow: auto;
  font-family: 'JetBrains Mono', Menlo, monospace; font-size: 12px;
  white-space: pre-wrap; word-break: break-all;
  margin-top: 12px;
}
</style>
