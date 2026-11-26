<template>
  <div class="stack" v-loading="loading">
    <PageHeader
      :icon="VideoCamera"
      :title="isEdit ? (isFinished ? '成片详情' : '制作详情') : '新建制作'"
      tone="lilac"
      :desc="isFinished
        ? '查看成片信息、发布平台与时间记录；播放数据请到「发布数据」录入'
        : '选择人物 / 场景 / 服装资产、创作平台，录入提示词与时间记录'"
    >
      <template #extra>
        <el-button @click="$router.back()">返回</el-button>
        <el-button type="primary" :loading="saving" @click="save">保存</el-button>
      </template>
    </PageHeader>

    <div class="edit-grid">
      <div class="edit-main">
        <!-- 基本信息 -->
        <el-card shadow="never" class="adm-card">
          <template #header><span class="adm-section-title">基本信息</span></template>
          <el-form label-width="96px" label-position="right">
            <el-form-item label="视频名称" required>
              <el-input v-model="form.title" placeholder="如：新买的人偶好好玩" />
            </el-form-item>

            <el-form-item label="封面截图">
              <div class="cover-edit">
                <ImageUploader
                  :src="form.cover"
                  mode="single"
                  shape="square"
                  :size="80"
                  @update:src="(url) => (form.cover = url)"
                />
                <span class="cover-tip">视频封面，用于列表缩略图展示</span>
              </div>
            </el-form-item>

            <el-form-item label="话题标签">
              <TagSelect v-model="form.tags" placeholder="从话题标签库选择，或输入新话题标签回车创建" />
            </el-form-item>

            <el-form-item label="参考链接">
              <el-input v-model="form.douyin_url" placeholder="参考视频的抖音链接（可选）" />
            </el-form-item>

            <el-form-item label="视频分类">
              <el-select v-model="form.category_id" placeholder="选填，在配置中心管理" clearable style="width: 100%">
                <el-option v-for="c in settings.categoryOptions" :key="c.id" :label="c.name" :value="c.id">
                  <OptionBadge :name="c.name" :color="c.color" :image="c.image" :display="c.display" />
                </el-option>
              </el-select>
            </el-form-item>

            <el-form-item label="资产选择">
              <el-tabs v-model="assetTab" class="asset-tabs">
                <el-tab-pane v-for="t in ASSET_TABS" :key="t.value" :label="t.label" :name="t.value">
                  <div class="char-picker">
                    <div
                      v-for="c in assetsByType(t.value)"
                      :key="c.id"
                      class="char-option"
                      :class="{ 'is-picked': pickedIds.includes(c.id) }"
                      @click="toggleCharacter(c.id)"
                    >
                      <el-image :src="c.images && c.images[0] ? c.images[0].file_path : ''" fit="cover" class="char-option-img">
                        <template #error>
                          <div class="char-option-img char-option-img--empty">
                            <el-icon :size="18"><component :is="t.icon" /></el-icon>
                          </div>
                        </template>
                      </el-image>
                      <div class="char-option-name">{{ c.name }}</div>
                      <el-icon v-if="pickedIds.includes(c.id)" class="char-check" :size="14"><Select /></el-icon>
                    </div>
                    <el-empty v-if="!assetsByType(t.value).length" :image-size="54" :description="`还没有${t.label}，请先到资产库创建`" />
                  </div>
                </el-tab-pane>
              </el-tabs>
            </el-form-item>

            <el-form-item v-if="pickedIds.length" label="角色 / 用途">
              <div class="role-list">
                <div v-for="c in pickedCharacters" :key="c.id" class="role-item">
                  <el-tag size="small" effect="plain">{{ assetTypeLabel(c.asset_type) }}</el-tag>
                  <span class="role-name">{{ c.name }}</span>
                  <el-select v-model="c.role" placeholder="角色" size="small" style="width: 110px">
                    <el-option v-for="r in CHARACTER_ROLES" :key="r" :label="r" :value="r" />
                  </el-select>
                  <el-button type="text" size="small" @click="toggleCharacter(c.id)">移除</el-button>
                </div>
              </div>
            </el-form-item>

            <el-row :gutter="12">
              <el-col :span="12">
                <el-form-item label="创作平台">
                  <el-select v-model="form.platform" placeholder="选择平台" clearable style="width: 100%">
                    <el-option
                      v-for="p in settings.platformOptions"
                      :key="p.name"
                      :label="p.name"
                      :value="p.name"
                    >
                      <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
                    </el-option>
                  </el-select>
                </el-form-item>
              </el-col>
              <el-col :span="12">
                <el-form-item label="制作状态">
                  <el-select v-model="form.status" style="width: 100%" @change="onStatusChange">
                    <el-option v-for="s in PRODUCTION_STATUS_OPTIONS" :key="s.value" :label="s.label" :value="s.value" />
                  </el-select>
                </el-form-item>
              </el-col>
            </el-row>

            <el-form-item label="提示词">
              <div class="prompt-editor">
                <div v-for="(seg, i) in form.prompt" :key="i" class="prompt-row">
                  <el-input v-model="seg.seg" placeholder="分段名" class="prompt-seg" />
                  <el-input v-model="seg.text" type="textarea" :rows="2" placeholder="提示词内容" class="prompt-text" />
                  <el-button type="text" class="danger-text" @click="form.prompt.splice(i, 1)">删除</el-button>
                </div>
                <el-button text :icon="Plus" @click="addSeg">添加分段</el-button>
              </div>
            </el-form-item>

            <el-form-item label="备注">
              <el-input v-model="form.remark" type="textarea" :rows="2" placeholder="补充说明" />
            </el-form-item>
          </el-form>
        </el-card>

        <!-- 发布信息：仅已完成 / 已发布显示 -->
        <el-card v-if="isFinished" shadow="never" class="adm-card" style="margin-top: 16px">
          <template #header><span class="adm-section-title">发布信息</span></template>
          <el-form label-width="96px" label-position="right">
            <el-form-item label="发布平台">
              <el-select v-model="form.publish_platform" placeholder="选择发布平台" filterable allow-create clearable style="width: 100%">
                <el-option v-for="p in settings.publishPlatformOptions" :key="p.name" :label="p.name" :value="p.name">
                  <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="发布账号">
              <el-select v-model="form.publish_account_id" placeholder="选择发布账号" clearable filterable style="width: 100%">
                <el-option v-for="a in accountOptions" :key="a.id" :label="`${a.name}（${a.platform}）`" :value="a.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="成片文件">
              <VideoUploader v-model="form.video_file" />
            </el-form-item>
            <el-form-item label="发布回链">
              <el-input v-model="form.published_url" placeholder="发布后的视频链接（可选）" />
            </el-form-item>
          </el-form>
          <el-alert type="info" :closable="false" show-icon title="数据录入"
            description="播放 / 点赞 / 评论 / 转发数据请到「发布数据」录入" />
        </el-card>
      </div>

      <!-- 右侧：时间线 + 参考 -->
      <div class="edit-side">
        <el-card shadow="never" class="adm-card">
          <template #header>
            <div class="table-head">
              <span class="adm-section-title">时间信息</span>
              <el-tag size="small" effect="plain">状态自动流转</el-tag>
            </div>
          </template>

          <div class="timeline">
            <div class="tl-item">
              <div class="tl-dot" :class="{ 'is-done': !!form.produced_at }" />
              <div class="tl-body">
                <div class="tl-label">制作时间</div>
                <el-date-picker v-model="form.produced_at" type="datetime" placeholder="未开始" size="small" style="width: 100%" />
              </div>
            </div>
            <div class="tl-item">
              <div class="tl-dot" :class="{ 'is-done': !!form.completed_at }" />
              <div class="tl-body">
                <div class="tl-label">完成时间</div>
                <el-date-picker v-model="form.completed_at" type="datetime" placeholder="未完成" size="small" style="width: 100%" />
              </div>
            </div>
            <div class="tl-item">
              <div class="tl-dot" :class="{ 'is-done': !!form.published_at }" />
              <div class="tl-body">
                <div class="tl-label">发布时间</div>
                <el-date-picker v-model="form.published_at" type="datetime" placeholder="未发布" size="small" style="width: 100%" />
              </div>
            </div>
          </div>

          <el-divider />
          <el-descriptions :column="1" border size="small">
            <el-descriptions-item label="创建人">{{ ownerName }}</el-descriptions-item>
            <el-descriptions-item label="创建时间">{{ formatDateTime(detail?.created_at) }}</el-descriptions-item>
            <el-descriptions-item label="更新时间">{{ formatDateTime(detail?.updated_at) }}</el-descriptions-item>
          </el-descriptions>
        </el-card>

        <el-card shadow="never" class="adm-card" style="margin-top: 16px">
          <template #header><span class="adm-section-title">参考视频</span></template>
          <el-input v-model="form.reference_url" placeholder="参考视频链接（可选）" />
          <el-form-item label="时长(秒)" style="margin-top: 12px">
            <el-input-number v-model="form.duration" :min="0" :precision="1" style="width: 100%" />
          </el-form-item>
        </el-card>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Plus, Select, User, VideoCamera, Picture, ShoppingBag } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import ImageUploader from '../components/ui/ImageUploader.vue'
import OptionBadge from '../components/ui/OptionBadge.vue'
import TagSelect from '../components/ui/TagSelect.vue'
import VideoUploader from '../components/ui/VideoUploader.vue'
import {
  api,
  CHARACTER_ROLES,
  PRODUCTION_STATUS_OPTIONS,
  formatDateTime
} from '../api'
import { useSettingsStore } from '../stores/settings'

const route = useRoute()
const settings = useSettingsStore()

const ASSET_TABS = [
  { value: 'character', label: '人物资产', icon: User },
  { value: 'scene', label: '场景资产', icon: Picture },
  { value: 'costume', label: '服装资产', icon: ShoppingBag }
]

const loading = ref(false)
const saving = ref(false)
const detail = ref(null)
const assetOptions = ref([])
const accountOptions = ref([])
const assetTab = ref('character')

const isEdit = computed(() => !!route.params.id)
const isFinished = computed(() => form.status === '已完成')

const form = reactive(emptyForm())

function emptyForm() {
  return {
    title: '', cover: '', tags: [], douyin_url: '', video_file: '',
    category_id: null, platform: '', publish_platform: '', publish_account_id: null, status: '制作中',
    prompt: [], reference_url: '', duration: null,
    produced_at: null, completed_at: null, published_at: null, published_url: '',
    remark: '', characters: []
  }
}

const pickedIds = computed(() => form.characters.map((c) => c.character_id))
const pickedCharacters = computed(() =>
  form.characters.map((c) => {
    const a = assetOptions.value.find((x) => x.id === c.character_id) || {}
    return { ...c, name: a.name || '未知资产', asset_type: a.asset_type || 'character' }
  })
)
const ownerName = computed(() => detail.value?.owner_name || '—')

function assetsByType(type) {
  return assetOptions.value.filter((a) => (a.asset_type || 'character') === type)
}

function assetTypeLabel(type) {
  const found = ASSET_TABS.find((t) => t.value === type)
  return found ? found.label.replace('资产', '') : '资产'
}

function toggleCharacter(id) {
  const idx = form.characters.findIndex((c) => c.character_id === id)
  if (idx >= 0) form.characters.splice(idx, 1)
  else form.characters.push({ character_id: id, role: form.characters.length ? '配角' : '主角', sort: form.characters.length })
}

function onStatusChange(v) {
  if (v === '已完成' && !form.publish_platform) {
    ElMessage.info('保存前请在「发布信息」中选择发布平台')
  }
}

function addSeg() {
  form.prompt.push({ seg: '', text: '' })
}

async function loadOptions() {
  try {
    const [assets, accounts] = await Promise.all([
      api.get('/characters', { params: { scope: 'all' } }),
      api.get('/publish-accounts', { params: { scope: 'all' } })
    ])
    assetOptions.value = (assets.data || []).filter((a) => ['character', 'scene', 'costume'].includes(a.asset_type || 'character'))
    accountOptions.value = accounts.data || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载选项失败')
  }
}

async function load() {
  loading.value = true
  try {
    if (isEdit.value) {
      const { data } = await api.get(`/productions/${route.params.id}`)
      detail.value = data
      Object.assign(form, {
        title: data.title || '', cover: data.cover || '', tags: [...(data.tags || [])],
        douyin_url: data.douyin_url || '', video_file: data.video_file || '',
        category_id: data.category_id || null, platform: data.platform || '',
        publish_platform: data.publish_platform || '', publish_account_id: data.publish_account_id || null,
        status: data.status || '制作中',
        prompt: (data.prompt || []).map((p) => ({ ...p })), reference_url: data.reference_url || '',
        duration: data.duration, produced_at: data.produced_at, completed_at: data.completed_at,
        published_at: data.published_at, published_url: data.published_url || '', remark: data.remark || '',
        characters: (data.characters || []).map((c) => ({
          character_id: c.character_id, role: c.role || '', sort: c.sort || 0
        }))
      })
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

async function save() {
  if (!form.title.trim()) return ElMessage.warning('请填写视频名称')
  if (form.status === '已完成' && !form.publish_platform) {
    return ElMessage.warning('已发布状态需要选择发布平台')
  }
  saving.value = true
  try {
    const payload = { ...form }
    if (isEdit.value) {
      const { data } = await api.put(`/productions/${route.params.id}`, payload)
      applyDetail(data)
      ElMessage.success('已保存')
    } else {
      const { data } = await api.post('/productions', payload)
      ElMessage.success('已创建')
      await router.replace(`/productions/${data.id}/edit`)
      applyDetail(data)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

function applyDetail(data) {
  detail.value = data
  form.produced_at = data.produced_at
  form.completed_at = data.completed_at
  form.published_at = data.published_at
  form.status = data.status
  form.category_id = data.category_id || null
  form.platform = data.platform
  form.publish_platform = data.publish_platform || ''
  form.characters = (data.characters || []).map((c) => ({
    character_id: c.character_id, role: c.role || '', sort: c.sort || 0
  }))
}

const router = useRouter()

onMounted(async () => {
  await settings.load()
  await loadOptions()
  await load()
})

watch(() => route.params.id, async (id) => { if (id) await load() })
</script>

<style scoped>
.edit-grid { display: grid; grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr); gap: 16px; align-items: start; }
.edit-main, .edit-side { min-width: 0; }
.opt-title { margin-right: 10px; }
.opt-tag { float: right; color: #909399; font-size: 12px; }
.link-preview { margin-top: 6px; display: flex; align-items: center; gap: 8px; flex-wrap: wrap; font-size: 12px; padding: 6px 10px; border-radius: 10px; background: rgba(64, 158, 255, 0.07); }
.link-label { color: var(--adm-text-secondary); }
.link-tags { color: var(--adm-text-placeholder); }

.char-picker { display: flex; flex-wrap: wrap; gap: 10px; width: 100%; min-height: 92px; }
.char-option { position: relative; width: 92px; padding: 6px; border-radius: 14px; border: 1.5px solid rgba(123, 163, 209, 0.2); background: var(--adm-panel); cursor: pointer; transition: all 0.18s ease; }
.char-option:hover { border-color: var(--el-color-primary); transform: translateY(-2px); }
.char-option.is-picked { border-color: var(--el-color-primary); background: rgba(64, 158, 255, 0.1); box-shadow: 0 6px 16px -6px rgba(64, 158, 255, 0.4); }
.char-option-img { width: 100%; height: 68px; border-radius: 10px; display: block; background: var(--adm-panel-soft); }
.char-option-img--empty { display: grid; place-items: center; color: var(--adm-text-placeholder); }
.char-option-name { margin-top: 5px; font-size: 12px; text-align: center; color: var(--adm-text-regular); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.char-check { position: absolute; top: 10px; right: 10px; width: 18px; height: 18px; border-radius: 50%; background: var(--el-color-primary); color: #fff; display: grid; place-items: center; }
.asset-tabs :deep(.el-tabs__header) { margin-bottom: 12px; }

.role-list { display: flex; flex-direction: column; gap: 6px; width: 100%; }
.role-item { display: flex; align-items: center; gap: 10px; padding: 6px 10px; border-radius: 10px; background: var(--adm-panel); border: 1px solid var(--adm-border); }
.role-name { font-size: 13px; color: var(--adm-text-primary); font-weight: 500; min-width: 90px; }

.prompt-editor { width: 100%; display: flex; flex-direction: column; gap: 8px; }
.prompt-row { display: flex; gap: 8px; align-items: flex-start; }
.prompt-seg { width: 130px; flex-shrink: 0; }
.prompt-text { flex: 1; }

.timeline { display: flex; flex-direction: column; gap: 14px; }
.tl-item { display: flex; gap: 12px; align-items: flex-start; }
.tl-dot { width: 10px; height: 10px; border-radius: 50%; margin-top: 6px; flex-shrink: 0; background: rgba(144, 147, 153, 0.35); border: 2px solid var(--adm-surface-solid); box-shadow: 0 0 0 1px rgba(123, 163, 209, 0.2); }
.tl-dot.is-done { background: var(--el-color-primary); box-shadow: 0 0 0 1px rgba(64, 158, 255, 0.4); }
.tl-body { flex: 1; min-width: 0; }
.tl-label { font-size: 12.5px; color: var(--adm-text-secondary); margin-bottom: 4px; }
.dot { display: inline-block; width: 8px; height: 8px; border-radius: 50%; margin-right: 4px; }
/* 图标显示模式下的平台选项 */
.platform-opt-icon { display: inline-grid; place-items: center; cursor: default; }
@media (max-width: 1100px) { .edit-grid { grid-template-columns: minmax(0, 1fr); } }
</style>
