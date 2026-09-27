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

        <el-tab-pane label="代理池" name="proxy">
          <div class="flex justify-between items-center mb-4">
            <div>
              <el-button type="primary" @click="proxyDialog = true">添加代理</el-button>
              <el-button @click="loadProxies">刷新</el-button>
              <el-input v-model="proxyTestUrl" placeholder="检测 URL" style="width: 240px; margin-left: 12px;" />
              <el-button @click="checkAllProxies">批量检测</el-button>
            </div>
          </div>
          <el-table :data="proxies" v-loading="proxyLoading" stripe>
            <el-table-column prop="name" label="名称" width="140" />
            <el-table-column prop="url" label="代理 URL" min-width="240" show-overflow-tooltip />
            <el-table-column prop="proxy_type" label="类型" width="80" />
            <el-table-column prop="region" label="地区" width="100" />
            <el-table-column prop="priority" label="优先级" width="80" />
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.last_check_ok === null ? 'info' : (row.last_check_ok ? 'success' : 'danger')" size="small">
                  {{ row.last_check_ok === null ? '未检测' : (row.last_check_ok ? '正常' : '失败') }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="统计" width="120">
              <template #default="{ row }">
                成功 {{ row.success_count }} / 失败 {{ row.failure_count }}
              </template>
            </el-table-column>
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-switch :model-value="row.is_active" @change="toggleProxy(row, $event)" />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="120">
              <template #default="{ row }">
                <el-button size="small" @click="editProxy(row)">编辑</el-button>
                <el-popconfirm title="确定删除？" @confirm="delProxy(row)">
                  <template #reference><el-button size="small" type="danger" plain>删除</el-button></template>
                </el-popconfirm>
              </template>
            </el-table-column>
          </el-table>

          <el-dialog v-model="proxyDialog" :title="proxyForm.id ? '编辑代理' : '添加代理'" width="500px">
            <el-form :model="proxyForm" label-width="100px">
              <el-form-item label="名称"><el-input v-model="proxyForm.name" placeholder="例：北京-1" /></el-form-item>
              <el-form-item label="URL"><el-input v-model="proxyForm.url" placeholder="http://user:pass@ip:port" /></el-form-item>
              <el-form-item label="类型">
                <el-select v-model="proxyForm.proxy_type" style="width: 100%;">
                  <el-option label="HTTP" value="http" />
                  <el-option label="HTTPS" value="https" />
                  <el-option label="SOCKS5" value="socks5" />
                </el-select>
              </el-form-item>
              <el-form-item label="地区"><el-input v-model="proxyForm.region" /></el-form-item>
              <el-form-item label="优先级"><el-input-number v-model="proxyForm.priority" :min="0" :max="999" /></el-form-item>
              <el-form-item label="启用"><el-switch v-model="proxyForm.is_active" /></el-form-item>
            </el-form>
            <template #footer>
              <el-button @click="proxyDialog = false">取消</el-button>
              <el-button type="primary" @click="saveProxy">保存</el-button>
            </template>
          </el-dialog>
        </el-tab-pane>

        <el-tab-pane label="Hyperbrowser" name="hyperbrowser">
          <el-alert
            title="Hyperbrowser 提供远程浏览器池（住宅IP + 真指纹），按会话计费。配置 HYPERBROWSER_API_KEY 后即可使用。"
            type="info" :closable="false" class="mb-4" />

          <el-card shadow="never" class="mb-4">
            <template #header>状态</template>
            <el-descriptions :column="2" border>
              <el-descriptions-item label="API Key">{{ hbStatus.configured ? '已配置' : '未配置' }}</el-descriptions-item>
              <el-descriptions-item label="活跃会话数">{{ hbStatus.active_sessions || 0 }}</el-descriptions-item>
            </el-descriptions>
          </el-card>

          <el-card shadow="never" v-if="hbStatus.sessions?.length">
            <template #header>会话列表</template>
            <el-table :data="hbStatus.sessions" stripe>
              <el-table-column prop="session_id" label="会话 ID" min-width="220" />
              <el-table-column prop="region" label="区域" width="100" />
              <el-table-column prop="expires_in_seconds" label="剩余秒数" width="120" />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button size="small" type="danger" plain @click="releaseSession(row.session_id)">释放</el-button>
                </template>
              </el-table-column>
            </el-table>
          </el-card>

          <div class="mt-4 flex gap-3">
            <el-button type="primary" @click="createSession" :disabled="!hbStatus.configured">手动创建会话</el-button>
            <el-button @click="loadHbStatus">刷新状态</el-button>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import http from '@/api'
import { ElMessage } from 'element-plus'
import {
  cleanerApi, classifierApi, downloadApi, suggestApi, engineApi,
  proxyApi, hyperbrowserApi,
} from '@/api/system'

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

// Proxy pool
const proxies = ref([])
const proxyLoading = ref(false)
const proxyDialog = ref(false)
const proxyForm = reactive({
  id: null, name: '', url: '', proxy_type: 'http',
  region: '', priority: 100, is_active: true,
})
const proxyTestUrl = ref('https://www.example.com/')

// Hyperbrowser
const hbStatus = ref({ configured: false, active_sessions: 0, sessions: [] })

async function loadStatus() {
  loadingStatus.value = true
  try {
    const { data } = await engineApi.status()
    tiers.value = Object.entries(data.tiers || {}).map(([name, info]) => ({
      name, ...info,
      error: info.error || (info.installed && info.configured ? '运行就绪' : '未安装或未配置'),
    }))
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

// Proxy pool
async function loadProxies() {
  proxyLoading.value = true
  try {
    const { data } = await proxyApi.list({ page_size: 100 })
    proxies.value = data.results || data
  } finally {
    proxyLoading.value = false
  }
}

async function saveProxy() {
  if (proxyForm.id) {
    await proxyApi.update(proxyForm.id, { ...proxyForm })
  } else {
    await proxyApi.create({ ...proxyForm })
  }
  ElMessage.success('已保存')
  proxyDialog.value = false
  Object.assign(proxyForm, { id: null, name: '', url: '' })
  loadProxies()
}

function editProxy(row) {
  Object.assign(proxyForm, row)
  proxyDialog.value = true
}

async function toggleProxy(row, val) {
  await proxyApi.update(row.id, { is_active: val })
  loadProxies()
}

async function delProxy(row) {
  await proxyApi.delete(row.id)
  ElMessage.success('已删除')
  loadProxies()
}

async function checkAllProxies() {
  ElMessage.info('正在批量检测代理，可能需要 30 秒以上...')
  try {
    const { data } = await proxyApi.checkAll(proxyTestUrl.value)
    ElMessage.success(`检测完成：${data.results.filter(r => r.ok).length} 正常 / ${data.results.filter(r => !r.ok).length} 失败`)
    loadProxies()
  } catch (e) {
    ElMessage.error('检测失败')
  }
}

// Hyperbrowser
async function loadHbStatus() {
  try {
    const { data } = await hyperbrowserApi.status()
    hbStatus.value = data
  } catch (e) {
    hbStatus.value = { configured: false, active_sessions: 0, sessions: [] }
  }
}

async function createSession() {
  try {
    await hyperbrowserApi.create()
    ElMessage.success('会话已创建')
    loadHbStatus()
  } catch (e) {
    ElMessage.error(e.response?.data?.error || '创建失败')
  }
}

async function releaseSession(sid) {
  try {
    await hyperbrowserApi.release(sid)
    ElMessage.success('已释放')
    loadHbStatus()
  } catch (e) {
    ElMessage.error('释放失败')
  }
}

onMounted(() => {
  loadStatus()
  loadSys()
  loadProxies()
  loadHbStatus()
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
