<template>
  <div class="stack">
    <PageHeader
      :icon="Setting"
      title="配置中心"
      tone="amber"
      desc="基础设置、分类与平台选项集中配置，并查看平台操作日志"
    />

    <div class="settings-grid">
      <!-- 基础设置：站点信息 / 抖音解析 / 投票规则 合并为一张卡片 -->
      <section class="adm-card settings-card settings-card--wide settings-card--fixed">
        <div class="settings-card-head">
          <span class="settings-icon is-blue"><el-icon :size="15"><Shop /></el-icon></span>
          <div class="settings-head-text">
            <div class="settings-title">基础设置</div>
            <div class="settings-desc">站点信息、链接解析规则与投票限制</div>
          </div>
        </div>
        <el-tabs v-model="basicTab" class="settings-tabs">
          <el-tab-pane label="站点信息" name="site">
            <el-form label-position="top">
              <div class="field-row">
                <el-form-item label="站点名称">
                  <el-input v-model="form.site.name" placeholder="视频资产管理" maxlength="20" show-word-limit @blur="persist('site', form.site)" />
                </el-form-item>
                <el-form-item label="副标题">
                  <el-input v-model="form.site.subtitle" placeholder="Assets Console" maxlength="24" show-word-limit @blur="persist('site', form.site)" />
                </el-form-item>
              </div>
            </el-form>
          </el-tab-pane>
          <el-tab-pane label="抖音解析" name="douyin">
            <div class="switch-list">
              <div class="switch-row">
                <div>
                  <div class="switch-label">获取视频 ID 用于去重</div>
                  <div class="switch-desc">后台轻量跟随短链取视频 ID 防重复；页面上的链接始终保留原始短链，不会替换成长链</div>
                </div>
                <el-switch v-model="form.douyin.auto_resolve" @change="persist('douyin', form.douyin)" />
              </div>
              <div class="switch-row">
                <div>
                  <div class="switch-label">从分享文案提取标题与话题标签</div>
                  <div class="switch-desc">解析文案中的标题与话题标签；作者始终不自动解析，可在新建计划时手动选填</div>
                </div>
                <el-switch v-model="form.douyin.auto_parse_title" @change="persist('douyin', form.douyin)" />
              </div>
              <div class="switch-row">
                <div>
                  <div class="switch-label">同一视频禁止重复建计划</div>
                  <div class="switch-desc">按抖音视频 ID 去重，避免同一素材重复进入待办池</div>
                </div>
                <el-switch v-model="form.douyin.reject_duplicate" @change="persist('douyin', form.douyin)" />
              </div>
              <div class="switch-row">
                <div>
                  <div class="switch-label">获取列表时自动勾选已导入作品</div>
                  <div class="switch-desc">发布数据页拉取作品列表后，已导入作品自动勾选并标记；只写入勾选的视频，取消勾选则不更新已有数据</div>
                </div>
                <el-switch v-model="form.douyin.auto_check_imported" @change="persist('douyin', form.douyin)" />
              </div>
            </div>
          </el-tab-pane>
          <el-tab-pane label="自动更新" name="auto_update">
            <div class="auto-update-panel">
              <div class="switch-row auto-update-switch">
                <div>
                  <div class="switch-label">启用每日自动更新</div>
                  <div class="switch-desc">每天到点自动检查在线账号并同步数据，离线账号跳过并推送页头提醒</div>
                </div>
                <el-switch v-model="form.auto_update.enabled" @change="persist('auto_update', form.auto_update)" />
              </div>
              <ol class="auto-update-rules">
                <li>到点先检查账号是否在线，离线账号不执行自动更新任务，并在页头消息中提醒重新登录</li>
                <li>更新范围：账号数据（作品数 / 获赞 / 粉丝）与视频发布数据</li>
                <li>每次更新自动写入历史快照，可在「我的账号 → 快照」中查看</li>
              </ol>
              <el-form label-position="top" class="auto-update-form">
                <div class="auto-update-fields">
                  <el-form-item label="每天执行时间">
                    <el-time-picker
                      v-model="autoUpdateTime"
                      format="HH:mm"
                      placeholder="选择执行时间"
                      style="width: 160px"
                      @change="persist('auto_update', form.auto_update)"
                    />
                    <div class="vote-tip">24 小时制，例如 08:30；同一天同一时间只执行一次</div>
                  </el-form-item>
                  <el-form-item label="每账号采集作品数">
                    <el-input-number
                      v-model="form.auto_update.video_limit"
                      :min="1"
                      :max="100"
                      style="width: 160px"
                      @change="persist('auto_update', form.auto_update)"
                    />
                    <div class="vote-tip">获取的最新作品数（含未采集写入作品）</div>
                  </el-form-item>
                </div>
              </el-form>
            </div>
          </el-tab-pane>
          <el-tab-pane label="投票规则" name="vote">
            <el-form label-position="top">
              <el-form-item label="每人每天投票次数上限">
                <el-input-number
                  v-model="form.vote.daily_limit"
                  :min="0"
                  :max="999"
                  style="width: 220px"
                  @change="persist('vote', form.vote)"
                />
                <div class="vote-tip">0 表示不允许投票；取消投票会返还当日次数</div>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </section>

      <!-- 选项配置：视频分类 / 创作平台 / 发布平台 合并为一张卡片 -->
      <section class="adm-card settings-card settings-card--wide settings-card--fixed">
        <div class="settings-card-head">
          <span class="settings-icon is-mint"><el-icon :size="15"><Files /></el-icon></span>
          <div class="settings-head-text">
            <div class="settings-title">选项配置</div>
            <div class="settings-desc">分类仅用颜色标签；平台图标与显示方式作用到全局</div>
          </div>
        </div>
        <el-tabs v-model="optionTab" class="settings-tabs">
          <el-tab-pane label="视频分类" name="category">
            <div class="option-toolbar">
              <span class="form-tip">颜色作用到全局，以文字标签展示，即时生效</span>
            </div>
            <div class="option-list">
              <div v-for="(c, idx) in categoryList" :key="c.id || 'new-' + idx" class="option-row is-option">
                <el-input v-model="c.name" size="small" placeholder="分类名称" maxlength="12" @blur="saveCategory(c)" @keyup.enter="saveCategory(c)" />
                <el-color-picker v-model="c.color" size="small" @change="saveCategory(c)" />
                <el-button size="small" :icon="Delete" @click="removeCategory(c)" />
              </div>
              <div v-if="!categoryList.length" class="option-empty">暂无分类，点「添加分类」后计划与制作页即可按颜色标签区分</div>
            </div>
            <div class="option-add-row">
              <button type="button" class="option-add-link" @click="addCategory"><el-icon><Plus /></el-icon>添加分类</button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="创作平台" name="platform">
            <div class="option-toolbar">
              <span class="display-mode-label">显示方式</span>
              <el-select v-model="form.display.platform" size="small" style="width: 116px" @change="saveDisplay">
                <el-option v-for="m in PLATFORM_DISPLAY_MODES" :key="m.value" :label="m.label" :value="m.value" />
              </el-select>
            </div>
            <div class="option-list">
              <div v-for="(p, idx) in form.platforms" :key="p._key || idx" class="option-row is-option">
                <ImageUploader
                  :src="p.image || ''"
                  mode="single"
                  shape="circle"
                  :size="30"
                  tip=""
                  @update:src="(url) => onPlatformImage(p, 'platforms', url)"
                />
                <el-input v-model="p.name" size="small" placeholder="平台名称" maxlength="16" @blur="savePlatform(p, 'platforms')" @keyup.enter="savePlatform(p, 'platforms')" />
                <el-color-picker v-model="p.color" size="small" @change="savePlatform(p, 'platforms')" />
                <el-button size="small" :icon="Delete" @click="removePlatform(p, 'platforms')" />
              </div>
              <div v-if="!form.platforms.length" class="option-empty">暂无平台，点「添加平台」后制作表单即可选择</div>
            </div>
            <div class="option-add-row">
              <button type="button" class="option-add-link" @click="addPlatform('platforms')"><el-icon><Plus /></el-icon>添加平台</button>
            </div>
          </el-tab-pane>
          <el-tab-pane label="发布平台" name="publish">
            <div class="option-toolbar">
              <span class="display-mode-label">显示方式</span>
              <el-select v-model="form.display.publish" size="small" style="width: 116px" @change="saveDisplay">
                <el-option v-for="m in PLATFORM_DISPLAY_MODES" :key="m.value" :label="m.label" :value="m.value" />
              </el-select>
            </div>
            <div class="option-list">
              <div v-for="(p, idx) in form.publish_platforms" :key="p._key || idx" class="option-row is-option">
                <ImageUploader
                  :src="p.image || ''"
                  mode="single"
                  shape="circle"
                  :size="30"
                  tip=""
                  @update:src="(url) => onPlatformImage(p, 'publish_platforms', url)"
                />
                <el-input v-model="p.name" size="small" placeholder="平台名称" maxlength="16" @blur="savePlatform(p, 'publish_platforms')" @keyup.enter="savePlatform(p, 'publish_platforms')" />
                <el-color-picker v-model="p.color" size="small" @change="savePlatform(p, 'publish_platforms')" />
                <el-button size="small" :icon="Delete" @click="removePlatform(p, 'publish_platforms')" />
              </div>
              <div v-if="!form.publish_platforms.length" class="option-empty">暂无发布平台，点「添加平台」后成品页即可选择</div>
            </div>
            <div class="option-add-row">
              <button type="button" class="option-add-link" @click="addPlatform('publish_platforms')"><el-icon><Plus /></el-icon>添加平台</button>
            </div>
          </el-tab-pane>
        </el-tabs>
      </section>

      <!-- 操作日志：替代话题标签库 -->
      <section class="adm-card settings-card settings-card--wide">
        <div class="settings-card-head">
          <span class="settings-icon is-lilac"><el-icon :size="15"><Document /></el-icon></span>
          <div class="settings-head-text">
            <div class="settings-title">操作日志</div>
            <div class="settings-desc">自动记录平台内的新增、编辑、删除与采集操作</div>
          </div>
          <el-button class="settings-head-add" size="small" type="danger" plain :icon="Delete" @click="clearLogs">清空日志</el-button>
        </div>
        <div class="log-toolbar">
          <el-select v-model="logFilter.module" placeholder="全部模块" clearable style="width: 140px" @change="onLogFilterChange">
            <el-option v-for="m in logModules" :key="m" :label="m" :value="m" />
          </el-select>
          <el-input
            v-model="logFilter.keyword"
            placeholder="搜索操作人 / 操作内容"
            clearable
            maxlength="50"
            style="width: 220px"
            :prefix-icon="Search"
            @keyup.enter="onLogFilterChange"
            @clear="onLogFilterChange"
          />
        </div>
        <div class="log-table-wrap">
          <el-table :data="logs" stripe size="small" v-loading="logLoading" empty-text="暂无操作日志">
            <el-table-column label="操作时间" width="160" align="right">
              <template #default="{ row }">
                <span class="adm-cell-time">{{ row.created_at }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作人" width="120" align="center">
              <template #default="{ row }">
                <span class="adm-cell-text">{{ row.username }}</span>
              </template>
            </el-table-column>
            <el-table-column label="模块" width="110" align="center">
              <template #default="{ row }">
                <el-tag size="small" effect="plain">{{ row.module }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <span class="log-action" :class="`is-${row.action}`">{{ row.action }}</span>
              </template>
            </el-table-column>
            <el-table-column label="对象" min-width="130" align="center">
              <template #default="{ row }">
                <span class="adm-cell-sub">{{ row.target || '—' }}</span>
              </template>
            </el-table-column>
            <el-table-column label="操作内容" min-width="240" align="left">
              <template #default="{ row }">
                <span class="log-summary">{{ row.summary }}</span>
              </template>
            </el-table-column>
            <el-table-column label="结果" width="80" align="center">
              <template #default="{ row }">
                <span class="log-status" :class="{ 'is-fail': row.status_code >= 400 }">
                  {{ row.status_code >= 400 ? '失败' : '成功' }}
                </span>
              </template>
            </el-table-column>
          </el-table>
        </div>
        <AppPagination
          v-model:page="logPage"
          v-model:page-size="logPageSize"
          :total="logTotal"
          always-show
          @page-size-change="onLogPageSizeChange"
        />
      </section>
    </div>

    <!-- 删除确认：点确认后弹窗立即关闭，成功/失败提示都不会被遮挡 -->
    <ConfirmDialog
      v-model="confirm.visible"
      :title="confirm.title"
      :message="confirm.message"
      :confirm-text="confirm.confirmText"
      :loading="confirm.loading"
      @confirm="onConfirm"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  Delete,
  Document,
  Files,
  Plus,
  Search,
  Setting,
  Shop
} from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import AppPagination from '../components/ui/AppPagination.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import ImageUploader from '../components/ui/ImageUploader.vue'
import { api } from '../api'
import { PLATFORM_DISPLAY_MODES } from '../api/platforms'
import { useSettingsStore } from '../stores/settings'

const settings = useSettingsStore()
const categoryList = ref([])
const basicTab = ref('site')
const optionTab = ref('category')

// 操作日志
const logs = ref([])
const logModules = ref([])
const logLoading = ref(false)
const logTotal = ref(0)
const logPage = ref(1)
const logPageSize = ref(10)
const logFilter = reactive({ module: '', keyword: '' })

const form = reactive({
  site: { name: '', subtitle: '' },
  douyin: { auto_resolve: true, auto_parse_title: true, reject_duplicate: true, auto_check_imported: true },
  auto_update: { enabled: true, hour: 8, minute: 0, video_limit: 20, sync_publish_data: true },
  vote: { daily_limit: 5 },
  display: { category: 'full', platform: 'full', publish: 'full' },
  platforms: [],
  publish_platforms: [],
  publish_accounts: []
})

const autoUpdateTime = computed({
  get: () => new Date(2000, 0, 1, Number(form.auto_update.hour) || 0, Number(form.auto_update.minute) || 0),
  set: (value) => {
    if (!(value instanceof Date)) return
    form.auto_update.hour = value.getHours()
    form.auto_update.minute = value.getMinutes()
  }
})

function readMode(value) {
  const mode = value && typeof value === 'object' ? value.mode : value
  return mode === 'label' || mode === 'icon' ? mode : 'full'
}

function normalizeAccount(a) {
  const src = typeof a === 'string' ? { name: a } : (a || {})
  return {
    platform: src.platform || '',
    account_id: src.account_id || '',
    name: src.name || '',
    avatar: src.avatar || '',
    tags: Array.isArray(src.tags) ? [...src.tags] : [],
    note: src.note || ''
  }
}

function assign(data) {
  form.site = { ...form.site, ...(data.site || {}) }
  form.douyin = { ...form.douyin, ...(data.douyin || {}) }
  form.auto_update = { ...form.auto_update, ...(data.auto_update || {}) }
  form.vote = { ...form.vote, ...(data.vote || {}) }
  const pd = data.platform_display || {}
  const legacy = readMode(pd)
  form.display = {
    category: 'label', // 视频分类固定为文字标签，不用图标
    platform: readMode(pd.platform ?? legacy),
    publish: readMode(pd.publish ?? legacy)
  }
  form.platforms = Array.isArray(data.platforms)
    ? data.platforms.map((p) => ({
        image: '', display: 'full', ...(typeof p === 'string' ? { name: p } : p)
      }))
    : []
  form.publish_platforms = Array.isArray(data.publish_platforms)
    ? data.publish_platforms.map((p) => ({
        image: '', display: 'full', ...(typeof p === 'string' ? { name: p } : p)
      }))
    : []
  form.publish_accounts = Array.isArray(data.publish_accounts)
    ? data.publish_accounts.map(normalizeAccount)
    : []
}

async function load() {
  await settings.load(true)
  assign(settings.items)
  await loadCategories()
  await loadLogs()
  await loadLogModules()
}

async function loadCategories() {
  try {
    const { data } = await api.get('/categories')
    categoryList.value = data.map((c) => ({ ...c }))
  } catch (e) {
    categoryList.value = []
  }
}

function onLogFilterChange() {
  logPage.value = 1
  loadLogs()
}

// 切每页条数时 AppPagination 会同时把页码重置为 1；
// 用标记吃掉这一次的页码 watch，避免与 page-size-change 重复发请求。
let skipNextPageWatch = false
function onLogPageSizeChange() {
  skipNextPageWatch = true
  logPage.value = 1
  loadLogs()
}

async function loadLogs() {
  logLoading.value = true
  try {
    const { data } = await api.get('/operation-logs', {
      params: {
        module: logFilter.module || '',
        keyword: logFilter.keyword || '',
        page: logPage.value,
        page_size: logPageSize.value
      }
    })
    logs.value = Array.isArray(data?.items) ? data.items : []
    logTotal.value = Number(data?.total || 0)
  } catch (e) {
    logs.value = []
    logTotal.value = 0
  } finally {
    logLoading.value = false
  }
}

async function loadLogModules() {
  try {
    const { data } = await api.get('/operation-logs/modules')
    logModules.value = Array.isArray(data) ? data : []
  } catch (e) {
    logModules.value = []
  }
}

watch(logPage, () => {
  if (skipNextPageWatch) {
    skipNextPageWatch = false
    return
  }
  loadLogs()
})

// 删除 / 清空确认：组件点确认时先关闭，这里只执行业务，提示不会被弹窗遮挡
const confirm = reactive({
  visible: false,
  title: '确认删除',
  message: '',
  confirmText: '确认删除',
  loading: false,
  kind: '',
  id: null,
  key: '',
  name: ''
})

function askConfirm(payload) {
  Object.assign(confirm, payload)
  confirm.visible = true
}

function onConfirm() {
  if (confirm.kind === 'category') return doRemoveCategory()
  if (confirm.kind === 'platform') return doRemovePlatform()
  if (confirm.kind === 'logs') return doClearLogs()
}

function clearLogs() {
  askConfirm({
    kind: 'logs',
    title: '清空日志',
    message: '确认清空全部操作日志？清空后无法恢复。',
    confirmText: '确认清空'
  })
}

async function doClearLogs() {
  try {
    await api.delete('/operation-logs')
    ElMessage.success('操作日志已清空')
    await loadLogs()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '清空失败')
  }
}

// 统一即时保存：失焦 / 开关 / 下拉变更后直接落库，不再需要点「保存配置」
async function persist(key, value) {
  try {
    await settings.save(key, value)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  }
}

async function saveDisplay() {
  await persist('platform_display', {
    mode: form.display.platform,
    category: form.display.category,
    platform: form.display.platform,
    publish: form.display.publish
  })
}

// 与创作平台 / 发布平台完全同款机制：点「添加」先插入一行空白，编辑后即时保存。
function addCategory() {
  if (categoryList.value.some((c) => !c.id)) return ElMessage.warning('请先填写上一条新增分类')
  categoryList.value.push({
    id: null, name: '', color: '#7b62c9', image: '', display: 'full', sort: categoryList.value.length, _draft: true
  })
}

async function saveCategory(c) {
  if (c._draft) {
    const name = (c.name || '').trim()
    if (!name) return // 空行保持草稿，不落库
    if (categoryList.value.some((x) => x.id && x.name === name)) {
      ElMessage.warning('分类已存在')
      return
    }
    try {
      const { data } = await api.post('/categories', {
        name, color: c.color || '#7b62c9', image: c.image || '', display: form.display.category, sort: c.sort || 0
      })
      Object.assign(c, data)
      c._draft = false
      ElMessage.success('分类已添加')
    } catch (e) {
      ElMessage.error(e.response?.data?.detail || '添加失败')
    }
    return
  }
  try {
    const { data } = await api.put(`/categories/${c.id}`, {
      name: (c.name || '').trim() || c.name,
      color: c.color || '#7b62c9',
      image: c.image || '',
      display: form.display.category,
      sort: c.sort || 0
    })
    Object.assign(c, data)
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '分类保存失败')
  }
}

function removeCategory(c) {
  if (c._draft) {
    categoryList.value = categoryList.value.filter((x) => x !== c)
    return
  }
  askConfirm({
    kind: 'category',
    title: '删除分类',
    message: `确定删除分类「${c.name}」吗？已有计划、创意或制作记录使用时将无法删除。`,
    id: c.id
  })
}

async function doRemoveCategory() {
  try {
    await api.delete(`/categories/${confirm.id}`)
    categoryList.value = categoryList.value.filter((x) => x.id !== confirm.id)
    await settings.loadCategories()
    ElMessage.success('分类已删除')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

// 制作 / 发布平台：草稿新增 + 失焦 / 改色 / 换图即时保存
function platformList(key) {
  return key === 'platforms' ? form.platforms : form.publish_platforms
}
function platformColor(key) {
  return key === 'platforms' ? '#4a7cc4' : '#e05c4b'
}

function addPlatform(key) {
  if (platformList(key).some((p) => p._draft)) return ElMessage.warning('请先填写上一条新增平台')
  platformList(key).push({ name: '', color: platformColor(key), image: '', display: 'full', _draft: true })
}

async function savePlatform(p, key) {
  const list = platformList(key)
  const name = (p.name || '').trim()
  if (p._draft) {
    if (!name) return // 空草稿不落库
    if (list.some((x) => x !== p && (x.name || '').trim() === name)) {
      ElMessage.warning('平台已存在')
      return
    }
    p.name = name
    p._draft = false
  }
  const mode = key === 'platforms' ? form.display.platform : form.display.publish
  await persist(key, list
    .filter((x) => (x.name || '').trim())
    .map((x) => ({
      name: (x.name || '').trim(),
      color: x.color || platformColor(key),
      image: x.image || '',
      display: mode
    })))
}

async function onPlatformImage(p, key, url) {
  p.image = url
  await savePlatform(p, key)
}

function removePlatform(p, key) {
  const list = platformList(key)
  if (p._draft) {
    list.splice(list.indexOf(p), 1)
    return
  }
  askConfirm({
    kind: 'platform',
    title: '删除平台',
    message: `确定删除平台「${p.name}」吗？已有业务记录使用时将无法删除。`,
    key,
    name: p.name
  })
}

async function doRemovePlatform() {
  try {
    await api.delete('/settings/option', { params: { key: confirm.key, name: confirm.name } })
    const list = platformList(confirm.key)
    const idx = list.findIndex((x) => (x.name || '').trim() === confirm.name)
    if (idx >= 0) list.splice(idx, 1)
    await settings.load(true)
    assign(settings.items)
    ElMessage.success('平台已删除')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

onMounted(load)
</script>

<style scoped>
.settings-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 16px;
}

.settings-card {
  padding: 18px 20px 20px;
  box-sizing: border-box;
  display: flex;
  flex-direction: column;
}
/* 基础设置 / 选项配置：高度固定，不随 tab 内容增减而改变容器高度 */
.settings-card--fixed {
  height: 380px;
}
.settings-card--fixed .settings-tabs {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
}
.settings-card--fixed :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;
}

.settings-tabs :deep(.el-tabs__header) {
  margin-bottom: 14px;
}

.settings-tabs :deep(.el-tabs__item) {
  font-size: 13px;
}

.option-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
  max-width: 740px;
}
.option-toolbar .form-tip {
  margin-top: 0;
  flex: 1;
  min-width: 0;
}
/* 选项添加按钮：与上方文本框（190px 宽）保持中心对齐 */
.option-add-row {
  display: flex;
  justify-content: center;
  width: 190px;
  max-width: 100%;
  margin-top: 10px;
}
.option-add-link {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  height: 28px;
  padding: 0 14px;
  border: 1px dashed var(--adm-border-deep);
  border-radius: 8px;
  background: transparent;
  color: var(--adm-text-secondary);
  font-size: 12px;
  cursor: pointer;
  transition: color 0.15s ease, border-color 0.15s ease, background-color 0.15s ease;
}
.option-add-link:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
}

/* 自动更新：规则说明独立成块，配置项紧凑对齐 */
.auto-update-panel {
  max-width: 660px;
}
.auto-update-switch {
  padding-bottom: 8px;
}
.auto-update-switch .switch-desc {
  max-width: 440px;
}
.auto-update-rules {
  margin: 2px 0 8px;
  padding: 6px 14px 6px 30px;
  border-radius: 8px;
  background: var(--adm-active-bg);
  color: var(--adm-text-secondary);
}
.auto-update-rules li {
  font-size: 11px;
  line-height: 1.5;
}
.auto-update-rules li::marker {
  color: var(--el-color-primary);
  font-weight: 600;
}
.auto-update-form {
  margin-top: 0;
}
.auto-update-fields {
  display: flex;
  gap: 24px;
}
.auto-update-fields :deep(.el-form-item) {
  flex: 1 1 0;
  min-width: 0;
  margin-bottom: 0;
}
.auto-update-fields .vote-tip {
  margin-top: 4px;
  line-height: 1.45;
}

/* 投票规则说明：换行独占一行 */
.vote-tip {
  width: 100%;
  margin-top: 6px;
  font-size: 12px;
  color: var(--adm-text-secondary);
  line-height: 1.6;
}

/* 基础设置：纵向排列，输入框限宽不拉成长条 */
.field-row {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.field-row :deep(.el-input__wrapper),
.settings-tabs :deep(.el-input-number) {
  max-width: 320px;
}

/* 选项配置：纵向单列排布，每行控件限宽 */
.settings-card .option-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 260px;
  overflow-y: auto;
  overflow-x: hidden;
  padding-right: 4px;
  box-sizing: border-box;
}
.settings-card .option-list::-webkit-scrollbar {
  width: 6px;
}
.settings-card .option-list::-webkit-scrollbar-thumb {
  background: var(--adm-border-deep);
  border-radius: 3px;
}

.option-row {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
}
.option-row :deep(.el-input) {
  flex: 0 1 190px;
  min-width: 90px;
  max-width: 240px;
}
.option-row :deep(.el-input-number) {
  max-width: 180px;
}

.option-empty {
  font-size: 12px;
  color: var(--adm-text-placeholder);
  padding: 8px 0;
}

.display-mode-label {
  font-size: 12.5px;
  color: var(--adm-text-secondary);
  white-space: nowrap;
}

/* 卡片头部 */
.settings-card-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 14px;
  min-height: 40px;
}
.settings-head-text {
  flex: 1;
  min-width: 0;
}
.settings-head-add {
  flex-shrink: 0;
  margin-left: 14px;
}

.settings-icon {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 10px;
  display: grid;
  place-items: center;
}
.settings-icon.is-blue {
  color: var(--adm-blue);
  background: var(--adm-blue-bg);
}
.settings-icon.is-mint {
  color: var(--adm-mint);
  background: var(--adm-mint-bg);
}
.settings-icon.is-lilac {
  color: var(--adm-lilac);
  background: var(--adm-lilac-bg);
}

.settings-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--adm-text-primary);
}
.settings-desc {
  font-size: 12px;
  color: var(--adm-text-secondary);
  margin-top: 1px;
}

.switch-list {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
/* 开关停靠在限宽容器右端，容器略收窄使开关左移一点 */
.switch-list {
  max-width: 660px;
}
.switch-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 10px 0;
  border-bottom: 1px dashed var(--adm-border);
}
.switch-row > div:first-child {
  flex: 1;
  min-width: 0;
}
.switch-row:last-child {
  border-bottom: none;
}
.switch-label {
  font-size: 13.5px;
  color: var(--adm-text-primary);
}
.switch-desc {
  font-size: 11.5px;
  color: var(--adm-text-secondary);
  margin-top: 2px;
  line-height: 1.5;
}

.settings-card :deep(.el-form-item) {
  margin-bottom: 14px;
}
.settings-card :deep(.el-form-item__label) {
  font-size: 12.5px;
  color: var(--adm-text-secondary);
  padding-bottom: 4px;
  line-height: 1.4;
}

/* 操作日志 */
.log-toolbar {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 14px;
}
.log-table-wrap {
  width: 100%;
  overflow-x: auto;
}
.page-size-select {
  width: 96px;
}
.page-size-select :deep(.el-select__wrapper) {
  min-height: 26px;
  font-size: 12px;
}
.log-action {
  font-size: 12px;
  font-weight: 600;
  color: var(--adm-text-regular);
}
.log-action.is-删除 { color: var(--el-color-danger); }
.log-action.is-新增 { color: var(--adm-mint); }
.log-action.is-编辑 { color: var(--el-color-primary); }
.log-summary {
  display: block;
  font-size: 13px;
  color: var(--adm-text-primary);
  line-height: 1.5;
}
.log-status {
  font-variant-numeric: tabular-nums;
  font-size: 12px;
  font-weight: 600;
  color: var(--adm-mint);
}
.log-status.is-fail { color: var(--el-color-danger); }
</style>
