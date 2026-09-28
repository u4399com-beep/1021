<template>
  <div class="page-container">
    <el-tabs v-model="tab">
      <el-tab-pane label="混淆配置" name="profiles">
        <el-card shadow="never">
          <div class="flex justify-between items-center mb-4">
            <div>
              <el-button @click="loadProfiles">刷新</el-button>
            </div>
            <div class="flex items-center gap-3">
              <el-select v-model="newProfileSiteId" placeholder="选择站点" filterable style="width: 240px;">
                <el-option v-for="s in sites" :key="s.id" :label="`${s.name} (${s.host})`" :value="s.id" />
              </el-select>
              <el-button type="primary" @click="createProfile" :disabled="!newProfileSiteId">创建配置</el-button>
            </div>
          </div>

          <el-table :data="profiles" v-loading="loading" stripe>
            <el-table-column prop="site_host" label="站点" width="200" />
            <el-table-column label="启用" width="80">
              <template #default="{ row }">
                <el-switch :model-value="row.enabled" @change="toggleEnabled(row, $event)" />
              </template>
            </el-table-column>
            <el-table-column label="HTML 结构" width="160">
              <template #default="{ row }">
                <span v-if="row.html_class_randomize" class="tag-on">类名</span>
                <span v-if="row.html_attr_order_shuffle" class="tag-on">属性</span>
                <span v-if="row.html_whitespace_noise" class="tag-on">空白</span>
                <span v-if="row.html_invisible_elements" class="tag-on">隐形</span>
              </template>
            </el-table-column>
            <el-table-column label="文本转码" width="160">
              <template #default="{ row }">
                <span v-if="row.transcode_full_width" class="tag-on">全角</span>
                <span v-if="row.transcode_homoglyph" class="tag-on">同形</span>
                <span v-if="row.transcode_zero_width" class="tag-on">零宽</span>
                <span v-if="row.transcode_punctuation" class="tag-on">标点</span>
              </template>
            </el-table-column>
            <el-table-column label="伪原创" width="160">
              <template #default="{ row }">
                <span v-if="row.rewrite_synonym" class="tag-on">同义</span>
                <span v-if="row.rewrite_sentence_reorder" class="tag-on">重排</span>
                <span v-if="row.rewrite_interference" class="tag-on">干扰</span>
              </template>
            </el-table-column>
            <el-table-column prop="updated_at" label="更新时间" width="170" />
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="editProfile(row)">编辑</el-button>
                <el-button size="small" type="danger" plain @click="quickToggle(row)">{{ row.enabled ? '禁用' : '启用' }}</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-dialog v-model="profileDialog" title="混淆配置" width="700px">
          <el-form :model="form" label-width="160px">
            <el-divider content-position="left">基本</el-divider>
            <el-form-item label="启用"><el-switch v-model="form.enabled" /></el-form-item>
            <el-form-item label="每请求重新生成种子"><el-switch v-model="form.seed_per_request" /></el-form-item>

            <el-divider content-position="left">Layer 1: HTML 结构混淆</el-divider>
            <el-form-item label="类名随机化"><el-switch v-model="form.html_class_randomize" /></el-form-item>
            <el-form-item label="属性顺序随机"><el-switch v-model="form.html_attr_order_shuffle" /></el-form-item>
            <el-form-item label="空白噪声"><el-switch v-model="form.html_whitespace_noise" /></el-form-item>
            <el-form-item label="隐形元素"><el-switch v-model="form.html_invisible_elements" /></el-form-item>
            <el-form-item label="注释噪声"><el-switch v-model="form.html_comment_inject" /></el-form-item>

            <el-divider content-position="left">Layer 2: 关键词/句子转码</el-divider>
            <el-form-item label="半角→全角"><el-switch v-model="form.transcode_full_width" /></el-form-item>
            <el-form-item label="同形字替换"><el-switch v-model="form.transcode_homoglyph" /></el-form-item>
            <el-form-item label="零宽字符"><el-switch v-model="form.transcode_zero_width" /></el-form-item>
            <el-form-item label="标点变体"><el-switch v-model="form.transcode_punctuation" /></el-form-item>
            <el-form-item label="转码密度">
              <el-slider v-model="form.transcode_density" :min="0" :max="1" :step="0.05" show-input />
            </el-form-item>

            <el-divider content-position="left">Layer 3: 伪原创重写</el-divider>
            <el-form-item label="同义词替换"><el-switch v-model="form.rewrite_synonym" /></el-form-item>
            <el-form-item label="句型重排"><el-switch v-model="form.rewrite_sentence_reorder" /></el-form-item>
            <el-form-item label="干扰句插入"><el-switch v-model="form.rewrite_interference" /></el-form-item>
            <el-form-item label="干扰句密度">
              <el-slider v-model="form.rewrite_interference_density" :min="0" :max="1" :step="0.05" show-input />
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="profileDialog = false">取消</el-button>
            <el-button type="primary" @click="saveProfile">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="同义词库" name="synonyms">
        <el-card shadow="never">
          <div class="flex justify-between items-center mb-4">
            <el-input v-model="synFilter.search" placeholder="搜索词" style="width: 240px;" @keyup.enter="loadSynonyms" />
            <el-button type="primary" @click="synDialog = true">添加同义词</el-button>
          </div>
          <el-table :data="synonyms" v-loading="synLoading" stripe>
            <el-table-column prop="word" label="原词" width="140" />
            <el-table-column label="同义词">
              <template #default="{ row }">
                <el-tag v-for="(s, i) in row.synonyms" :key="i" size="small" effect="plain" style="margin-right: 4px;">{{ s }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column label="启用" width="80"><template #default="{ row }"><el-switch :model-value="row.enabled" @change="toggleSyn(row, $event)" /></template></el-table-column>
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" @click="editSyn(row)">编辑</el-button>
                <el-popconfirm title="删除？" @confirm="delSyn(row)"><template #reference><el-button size="small" type="danger" plain>删除</el-button></template></el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-dialog v-model="synDialog" :title="synForm.id ? '编辑同义词' : '添加同义词'" width="500px">
          <el-form :model="synForm" label-width="80px">
            <el-form-item label="原词"><el-input v-model="synForm.word" /></el-form-item>
            <el-form-item label="同义词">
              <el-input v-model="synForm.synonymsStr" type="textarea" :rows="3" placeholder="逗号分隔" />
            </el-form-item>
            <el-form-item label="分类">
              <el-select v-model="synForm.category" style="width: 100%;">
                <el-option label="通用" value="general" />
                <el-option label="动词" value="verb" />
                <el-option label="名词" value="noun" />
                <el-option label="形容词" value="adj" />
                <el-option label="副词" value="adv" />
              </el-select>
            </el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="synDialog = false">取消</el-button>
            <el-button type="primary" @click="saveSyn">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="干扰句库" name="interferences">
        <el-card shadow="never">
          <div class="flex justify-between items-center mb-4">
            <el-input v-model="intFilter.search" placeholder="搜索" style="width: 240px;" @keyup.enter="loadInterferences" />
            <el-button type="primary" @click="intDialog = true">添加干扰句</el-button>
          </div>
          <el-table :data="interferences" v-loading="intLoading" stripe>
            <el-table-column label="句子内容" min-width="400"><template #default="{ row }">{{ row.text }}</template></el-table-column>
            <el-table-column prop="category" label="分类" width="100" />
            <el-table-column prop="weight" label="权重" width="80" />
            <el-table-column prop="used_count" label="已用" width="80" />
            <el-table-column label="操作" width="160">
              <template #default="{ row }">
                <el-button size="small" @click="editInt(row)">编辑</el-button>
                <el-popconfirm title="删除？" @confirm="delInt(row)"><template #reference><el-button size="small" type="danger" plain>删除</el-button></template></el-popconfirm>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <el-dialog v-model="intDialog" :title="intForm.id ? '编辑干扰句' : '添加干扰句'" width="500px">
          <el-form :model="intForm" label-width="80px">
            <el-form-item label="句子"><el-input v-model="intForm.text" type="textarea" :rows="3" /></el-form-item>
            <el-form-item label="分类">
              <el-select v-model="intForm.category" style="width: 100%;">
                <el-option label="通用" value="general" />
                <el-option label="场景" value="scene" />
                <el-option label="对话" value="dialogue" />
                <el-option label="旁白" value="narration" />
              </el-select>
            </el-form-item>
            <el-form-item label="权重"><el-input-number v-model="intForm.weight" :step="0.5" :min="0" /></el-form-item>
          </el-form>
          <template #footer>
            <el-button @click="intDialog = false">取消</el-button>
            <el-button type="primary" @click="saveInt">保存</el-button>
          </template>
        </el-dialog>
      </el-tab-pane>

      <el-tab-pane label="预览测试" name="preview">
        <el-card shadow="never">
          <el-form label-width="100px">
            <el-form-item label="目标站点">
              <el-select v-model="previewForm.site_id" placeholder="选站点" filterable style="width: 300px;">
                <el-option v-for="s in sites" :key="s.id" :label="`${s.name} (${s.host})`" :value="s.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="测试文本">
              <el-input v-model="previewForm.text" type="textarea" :rows="6"
                placeholder="<p>他看了一眼天空，然后笑了。风吹过，带着远方的气息。</p>" />
            </el-form-item>
            <el-form-item label="分层">
              <el-checkbox v-model="previewForm.html_structure">HTML 结构混淆</el-checkbox>
              <el-checkbox v-model="previewForm.transcode">文本转码</el-checkbox>
              <el-checkbox v-model="previewForm.rewrite">伪原创</el-checkbox>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="previewing" @click="runPreview">运行预览</el-button>
            </el-form-item>
          </el-form>

          <el-divider />

          <div v-if="previewResult">
            <el-descriptions :column="2" border class="mb-4">
              <el-descriptions-item label="原始大小">{{ previewResult.original_size }} bytes</el-descriptions-item>
              <el-descriptions-item label="结构混淆">{{ previewResult.sizes.html_structure || 0 }} bytes</el-descriptions-item>
              <el-descriptions-item label="转码">{{ previewResult.sizes.transcode || 0 }} bytes</el-descriptions-item>
              <el-descriptions-item label="重写">{{ previewResult.sizes.rewrite || 0 }} bytes</el-descriptions-item>
              <el-descriptions-item label="全流程">{{ previewResult.sizes.full || 0 }} bytes</el-descriptions-item>
            </el-descriptions>

            <el-tabs>
              <el-tab-pane label="原始">
                <pre class="preview-box">{{ previewResult.original }}</pre>
              </el-tab-pane>
              <el-tab-pane label="结构混淆">
                <pre class="preview-box">{{ previewResult.results.html_structure }}</pre>
              </el-tab-pane>
              <el-tab-pane label="转码">
                <pre class="preview-box">{{ previewResult.results.transcode }}</pre>
              </el-tab-pane>
              <el-tab-pane label="重写">
                <pre class="preview-box">{{ previewResult.results.rewrite }}</pre>
              </el-tab-pane>
              <el-tab-pane label="全流程">
                <pre class="preview-box">{{ previewResult.results.full }}</pre>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { obfuscatorApi } from '@/api/obfuscator'
import { siteApi } from '@/api/site'

const tab = ref('profiles')

const profiles = ref([])
const sites = ref([])
const loading = ref(false)
const profileDialog = ref(false)
const newProfileSiteId = ref(null)

const form = reactive({
  id: null, site: null, enabled: false,
  html_class_randomize: true, html_attr_order_shuffle: true,
  html_whitespace_noise: true, html_invisible_elements: true, html_comment_inject: true,
  transcode_full_width: false, transcode_homoglyph: false,
  transcode_zero_width: false, transcode_punctuation: true, transcode_density: 0.15,
  rewrite_synonym: false, rewrite_sentence_reorder: false,
  rewrite_interference: false, rewrite_interference_density: 0.3,
  seed_per_request: true,
})

// Synonyms
const synonyms = ref([])
const synLoading = ref(false)
const synFilter = reactive({ search: '' })
const synDialog = ref(false)
const synForm = reactive({ id: null, word: '', synonymsStr: '', category: 'general', enabled: true })

// Interferences
const interferences = ref([])
const intLoading = ref(false)
const intFilter = reactive({ search: '' })
const intDialog = ref(false)
const intForm = reactive({ id: null, text: '', category: 'general', weight: 1.0, enabled: true })

// Preview
const previewForm = reactive({
  site_id: null, text: '<p>他看了一眼天空，然后笑了。风吹过，带着远方的气息。</p>',
  html_structure: true, transcode: true, rewrite: true,
})
const previewResult = ref(null)
const previewing = ref(false)

async function loadProfiles() {
  loading.value = true
  try {
    const { data } = await obfuscatorApi.listProfiles({ page_size: 100 })
    profiles.value = data.results || data
  } finally { loading.value = false }
}

async function loadSites() {
  const { data } = await siteApi.list({ page_size: 100 })
  sites.value = data.results || data
}

async function createProfile() {
  if (!newProfileSiteId.value) return
  await obfuscatorApi.createProfile({ site: newProfileSiteId.value, enabled: false })
  ElMessage.success('已创建，请编辑')
  newProfileSiteId.value = null
  loadProfiles()
}

function editProfile(row) {
  Object.assign(form, row)
  profileDialog.value = true
}

async function saveProfile() {
  if (form.id) {
    await obfuscatorApi.updateProfile(form.id, form)
  }
  ElMessage.success('已保存')
  profileDialog.value = false
  loadProfiles()
}

async function toggleEnabled(row, val) {
  await obfuscatorApi.updateProfile(row.id, { enabled: val })
  loadProfiles()
}

async function quickToggle(row) {
  await obfuscatorApi.updateProfile(row.id, { enabled: !row.enabled })
  ElMessage.success(row.enabled ? '已禁用' : '已启用')
  loadProfiles()
}

// Synonyms
async function loadSynonyms() {
  synLoading.value = true
  try {
    const { data } = await obfuscatorApi.listSynonyms({ page_size: 200, search: synFilter.search })
    synonyms.value = data.results || data
  } finally { synLoading.value = false }
}

function editSyn(row) {
  Object.assign(synForm, row, { synonymsStr: (row.synonyms || []).join(', ') })
  synDialog.value = true
}

async function saveSyn() {
  const payload = {
    ...synForm,
    synonyms: synForm.synonymsStr.split(/[,，]/).map(s => s.trim()).filter(Boolean),
  }
  delete payload.synonymsStr
  if (synForm.id) {
    await obfuscatorApi.updateSynonym(synForm.id, payload)
  } else {
    await obfuscatorApi.createSynonym(payload)
  }
  ElMessage.success('已保存')
  synDialog.value = false
  Object.assign(synForm, { id: null, word: '', synonymsStr: '', category: 'general' })
  loadSynonyms()
}

async function toggleSyn(row, val) {
  await obfuscatorApi.updateSynonym(row.id, { enabled: val })
  loadSynonyms()
}

async function delSyn(row) {
  await obfuscatorApi.deleteSynonym(row.id)
  ElMessage.success('已删除')
  loadSynonyms()
}

// Interferences
async function loadInterferences() {
  intLoading.value = true
  try {
    const { data } = await obfuscatorApi.listInterferences({ page_size: 200, search: intFilter.search })
    interferences.value = data.results || data
  } finally { intLoading.value = false }
}

function editInt(row) {
  Object.assign(intForm, row)
  intDialog.value = true
}

async function saveInt() {
  if (intForm.id) {
    await obfuscatorApi.updateInterference(intForm.id, intForm)
  } else {
    await obfuscatorApi.createInterference(intForm)
  }
  ElMessage.success('已保存')
  intDialog.value = false
  Object.assign(intForm, { id: null, text: '', category: 'general', weight: 1.0 })
  loadInterferences()
}

async function delInt(row) {
  await obfuscatorApi.deleteInterference(row.id)
  ElMessage.success('已删除')
  loadInterferences()
}

// Preview
async function runPreview() {
  previewing.value = true
  try {
    const { data } = await obfuscatorApi.preview(previewForm)
    previewResult.value = data
  } catch (e) {
    ElMessage.error('预览失败')
  } finally {
    previewing.value = false
  }
}

onMounted(() => {
  loadProfiles()
  loadSites()
  loadSynonyms()
  loadInterferences()
})
</script>

<style scoped lang="scss">
.tag-on {
  display: inline-block;
  margin-right: 4px;
  padding: 1px 6px;
  font-size: 11px;
  background: rgba(64, 158, 255, 0.1);
  color: #409eff;
  border-radius: 3px;
}
.preview-box {
  background: #1e1e1e; color: #d4d4d4;
  padding: 12px; border-radius: 4px;
  max-height: 400px; overflow: auto;
  font-family: 'JetBrains Mono', Menlo, monospace; font-size: 12px;
  white-space: pre-wrap; word-break: break-all;
}
</style>
