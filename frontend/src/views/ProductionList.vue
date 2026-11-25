<template>
  <div class="stack">
    <PageHeader
      :icon="VideoCamera"
      title="视频创作"
      tone="lilac"
      desc="第二步 · 选择人物 / 场景 / 服装资产、制作平台与提示词；完成后状态更新为已发布"
    >
      <template #extra>
        <el-input v-model="keyword" placeholder="搜索名称" clearable style="width: 180px" @keyup.enter="load">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="platform" placeholder="制作平台" clearable style="width: 130px" @change="load">
          <el-option v-for="p in settings.platformOptions" :key="p.name" :label="p.name" :value="p.name">
            <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
          </el-option>
        </el-select>
        <el-select v-model="scope" style="width: 120px" @change="load">
          <el-option value="all" label="全部成员" />
          <el-option value="mine" label="仅我的" />
        </el-select>
        <el-button
          v-if="perm.can('productions.create')"
          type="primary"
          :icon="Plus"
          @click="openCreate"
        >新增制作</el-button>
      </template>
    </PageHeader>

    <div class="stat-row">
      <StatCard
        v-for="s in statCards"
        :key="s.label"
        :label="s.label"
        :value="s.value"
        :icon="s.icon"
        :tone="s.tone"
      />
    </div>

    <el-card shadow="never" class="adm-card adm-card--table" :class="{ 'is-loading': loading }">
      <GridSkeleton v-if="loading" :rows="8" :cols="6" />
      <div class="adm-table-wrap">
        <el-table :data="pagedList" stripe style="width: 100%" empty-text="还没有创作记录，可点右上角「新增制作」">
          <!-- 封面 + 视频名称（第二行作者 + 类别） -->
          <el-table-column label="封面" width="72" align="center">
            <template #default="{ row }">
              <div class="adm-cell-cover">
                <img v-if="row.cover" :src="row.cover" class="adm-cover-thumb" :alt="row.title" />
                <img v-else src="/placeholder.svg" class="adm-cover-thumb is-empty" alt="暂无封面" />
              </div>
            </template>
          </el-table-column>

          <el-table-column label="视频名称" min-width="180" align="left">
            <template #default="{ row }">
              <a
                v-if="row.douyin_url"
                :href="row.douyin_url"
                target="_blank"
                rel="noopener"
                class="adm-cell-link adm-cell-text adm-cell-text--clamp2"
                :title="(row.title || '未命名制作') + ' · 点击打开抖音'"
              >{{ row.title || '未命名制作' }}</a>
              <span v-else class="adm-cell-text adm-cell-text--clamp2" :title="row.title || '未命名制作'">
                {{ row.title || '未命名制作' }}
              </span>
              <div class="adm-cell-sub">
                <span class="idea-author" :title="row.author || '未获取作者'">@{{ row.author || '未获取' }}</span>
                <OptionBadge
                  v-if="row.category_name"
                  :name="row.category_name"
                  :color="settings.option('category', row.category_name).color"
                  :image="settings.option('category', row.category_name).image"
                  :display="settings.option('category', row.category_name).display"
                />
                <span v-else class="adm-cell-empty">—</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="使用资产" min-width="124" align="left">
            <template #default="{ row }">
              <div v-if="row.characters && row.characters.length" class="char-cell">
                <el-image
                  v-for="c in row.characters.slice(0, 3)"
                  :key="c.id"
                  :src="c.character_cover || '/placeholder.svg'"
                  fit="cover"
                  class="char-avatar"
                  :title="c.character_name + (c.role ? ' · ' + c.role : '')"
                >
                  <template #error><img src="/placeholder.svg" class="char-avatar" alt="暂无资产" /></template>
                </el-image>
                <span class="char-names" :title="row.characters.map((c) => c.character_name).join('、')">{{ row.characters.map((c) => c.character_name).join('、') }}</span>
              </div>
              <span v-else class="adm-cell-empty">未绑定</span>
            </template>
          </el-table-column>

          <el-table-column label="制作平台" min-width="100" align="center">
            <template #default="{ row }">
              <OptionBadge
                v-if="row.platform"
                :name="row.platform"
                :color="settings.option('platform', row.platform).color"
                :image="settings.option('platform', row.platform).image"
                :display="settings.option('platform', row.platform).display"
              />
              <span v-else class="adm-cell-empty">—</span>
            </template>
          </el-table-column>

          <el-table-column label="状态" min-width="100" align="center">
            <template #default="{ row }">
              <button
                type="button"
                class="prod-status-btn"
                :disabled="!canChangeStatus(row) || !['制作中', '待发布'].includes(row.status)"
                :title="statusClickTitle(row)"
                @click="openStatusConfirm(row)"
              >
                <el-tag :type="productionStatusType(row.status)" size="small" effect="light">{{ productionStatusLabel(row.status) }}</el-tag>
              </button>
            </template>
          </el-table-column>

          <el-table-column label="创作时间" min-width="140" align="left">
            <template #default="{ row }">
              <div class="prod-time-cell">
                <span class="prod-time-row is-start">
                  <el-icon :size="12"><VideoPlay /></el-icon>
                  <span>开始</span>
                  <span class="adm-cell-time">{{ row.produced_at ? formatDateTime(row.produced_at) : '—' }}</span>
                </span>
                <span class="prod-time-row is-done">
                  <el-icon :size="12"><CircleCheckFilled /></el-icon>
                  <span>完成</span>
                  <span class="adm-cell-time">{{ row.completed_at ? formatDateTime(row.completed_at) : '—' }}</span>
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="创作人" min-width="96" align="center">
            <template #default="{ row }">
              <el-tag size="small" effect="plain" :type="row.is_owner ? 'primary' : 'info'">
                {{ row.owner_name }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="提示词" min-width="92" align="left">
            <template #default="{ row }">
              <span v-if="row.prompt && row.prompt.length" class="adm-cell-text adm-cell-text--clamp2"
                :title="row.prompt.map((p) => `${p.seg}：${p.text || ''}`).join('；')">
                {{ row.prompt.map((p) => p.seg).join(' / ') }}
              </span>
              <span v-else class="adm-cell-empty">—</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" min-width="120" fixed="right" align="center">
            <template #default="{ row }">
              <div class="adm-cell-actions">
                <el-button v-if="perm.can('productions.edit') && (row.is_owner || auth.isAdmin)" type="text" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button v-if="perm.can('productions.delete') && (row.is_owner || auth.isAdmin)" type="text" size="small" class="danger-text" @click="remove(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :image-size="100" description="还没有创作记录" />
          </template>
        </el-table>
      </div>

      <AppPagination v-model:page="page" :total="list.length" v-model:page-size="PAGE_SIZE" />
    </el-card>

    <!-- 新建弹窗：不依赖参考视频，手动创建制作记录 -->
    <el-dialog
      v-model="create.visible"
      width="640px"
      class="adm-dialog-detail edit-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <DialogHeader
          :icon="VideoCamera"
          title="新增视频制作"
          sub="不依赖参考视频 · 封面使用默认图"
          tone="lilac"
        />
      </template>
      <div class="edit-dialog-body" v-loading="create.loading">
        <el-form label-width="96px" label-position="right">
          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-primary" />基础信息</h4>
            <el-form-item label="视频名称" required>
              <el-input v-model="create.form.title" placeholder="请输入视频名称" maxlength="200" />
            </el-form-item>
            <el-form-item label="类型" required>
              <el-select v-model="create.form.category_id" placeholder="选择视频分类" clearable filterable style="width: 100%">
                <el-option v-for="c in settings.categoryOptions" :key="c.id" :label="c.name" :value="c.id">
                  <OptionBadge :name="c.name" :color="c.color" :image="c.image" :display="c.display" />
                </el-option>
              </el-select>
            </el-form-item>
          </section>

          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-mint" />制作信息</h4>
            <el-form-item label="使用资产" required>
              <el-select
                v-model="create.form.characterIds"
                multiple
                filterable
                clearable
                style="width: 100%"
                placeholder="选择人物资产（可多选）"
              >
                <el-option v-for="a in characterOptions" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="制作平台" required>
              <el-select v-model="create.form.platform" placeholder="选择平台" clearable filterable style="width: 100%">
                <el-option v-for="p in settings.platformOptions" :key="p.name" :label="p.name" :value="p.name">
                  <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="提示词" required>
              <el-input
                v-model="create.form.promptText"
                type="textarea"
                :rows="5"
                maxlength="2500"
                show-word-limit
                placeholder="输入完整提示词（最多 2500 字）"
                class="prompt-textarea"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="create.form.remark" type="textarea" :rows="2" placeholder="补充说明" />
            </el-form-item>
          </section>
        </el-form>

        <div class="edit-dialog-footer">
          <el-button type="primary" plain @click="create.visible = false">取消</el-button>
          <el-button type="primary" :loading="create.saving" @click="doCreate">创建</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 编辑弹窗：直接编辑制作字段，无需跳转详情页 -->
    <el-dialog
      v-model="edit.visible"
      width="640px"
      class="adm-dialog-detail edit-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <DialogHeader
          :icon="VideoCamera"
          :title="edit.form.title || '编辑制作'"
          sub="视频创作 · 直接修改字段后保存"
          tone="lilac"
        />
      </template>

      <div class="edit-dialog-body" v-loading="edit.loading">
        <el-form label-width="96px" label-position="right">
          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-primary" />参考视频</h4>
            <div class="ref-video-view">
              <img v-if="edit.form.cover" :src="edit.form.cover" class="ref-cover" alt="参考视频封面" />
              <img v-else src="/placeholder.svg" class="ref-cover is-empty" alt="暂无封面" />
              <div class="ref-video-info">
                <a
                  v-if="edit.form.douyin_url"
                  :href="edit.form.douyin_url"
                  target="_blank"
                  rel="noopener"
                  class="ref-title ref-title-link"
                  :title="`点击打开抖音：${edit.form.title || '未命名视频'}`"
                >{{ edit.form.title || '未命名视频' }}</a>
                <div v-else class="ref-title">{{ edit.form.title || '未命名视频' }}</div>
                <div class="ref-tags">
                  <template v-if="edit.form.tags && edit.form.tags.length">
                    <span v-for="t in edit.form.tags" :key="t" class="adm-tag-chip">#{{ t }}</span>
                  </template>
                  <span v-else class="adm-cell-empty">—</span>
                </div>
                <!-- 只读项：类型 / 制作人 / 状态，放在参考视频卡片内，不带小标题 -->
                <div class="readonly-row">
                  <div class="readonly-item">
                    <OptionBadge
                      v-if="categoryName(edit.form.category_id)"
                      :name="categoryName(edit.form.category_id)"
                      :color="settings.option('category', categoryName(edit.form.category_id)).color"
                      :image="settings.option('category', categoryName(edit.form.category_id)).image"
                      :display="settings.option('category', categoryName(edit.form.category_id)).display"
                    />
                    <span v-else class="adm-cell-empty">—</span>
                  </div>
                  <div class="readonly-item">
                    <el-tag size="small" effect="plain">{{ edit.form.ownerName || '未指定' }}</el-tag>
                  </div>
                  <div class="readonly-item">
                    <el-tag :type="productionStatusType(edit.form.status)" size="small" effect="light">{{ productionStatusLabel(edit.form.status) }}</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-mint" />制作信息</h4>
            <el-form-item label="使用资产">
              <el-select
                v-model="edit.form.characterIds"
                multiple
                filterable
                clearable
                style="width: 100%"
                placeholder="选择人物资产（可多选）"
              >
                <el-option v-for="a in characterOptions" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="制作平台">
              <el-select v-model="edit.form.platform" placeholder="选择平台" clearable filterable style="width: 100%">
                <el-option v-for="p in settings.platformOptions" :key="p.name" :label="p.name" :value="p.name">
                  <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="提示词">
              <el-input
                v-model="edit.form.promptText"
                type="textarea"
                :rows="5"
                maxlength="2500"
                show-word-limit
                placeholder="输入完整提示词（最多 2500 字）"
                class="prompt-textarea"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="edit.form.remark" type="textarea" :rows="2" placeholder="补充说明" />
            </el-form-item>
          </section>
        </el-form>

        <div class="edit-dialog-footer">
          <el-button type="primary" plain @click="edit.visible = false">取消</el-button>
          <el-button type="primary" :loading="edit.saving" @click="doEdit">保存</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 状态确认：制作中确认完成→待发布；待发布确认还原→制作中 -->
    <ConfirmDialog
      v-model="statusConfirm.visible"
      :title="statusConfirm.title"
      :message="statusConfirm.message"
      :loading="statusConfirm.loading"
      :confirm-text="statusConfirm.confirmText"
      :variant="statusConfirm.variant"
      :icon="statusConfirm.icon"
      @confirm="doChangeStatus"
    />

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="confirm.visible"
      :title="confirm.title"
      :message="confirm.message"
      :loading="confirm.loading"
      @confirm="doRemove"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Loading, Plus, Search, Timer, VideoCamera, VideoPlay } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import AppPagination from '../components/ui/AppPagination.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import OptionBadge from '../components/ui/OptionBadge.vue'
import StatCard from '../components/ui/StatCard.vue'
import { api, formatDateTime, productionStatusLabel, productionStatusType } from '../api'
import { useAuthStore } from '../stores/auth'
import { usePermissionStore } from '../stores/permission'
import { useSettingsStore } from '../stores/settings'

const auth = useAuthStore()
const perm = usePermissionStore()
const settings = useSettingsStore()
const router = useRouter()

const PAGE_SIZE = ref(12)

const loading = ref(false)
const list = ref([])
const keyword = ref('')
const platform = ref('')
const scope = ref('all')
const page = ref(1)
const characterOptions = ref([])
const confirm = reactive({ visible: false, loading: false, title: '', message: '', id: null })
const statusConfirm = reactive({
  visible: false, loading: false, row: null, target: '',
  title: '', message: '', confirmText: '', variant: 'success', icon: 'success'
})
// 四项统计：内部「已完成」在展示层即为「已发布」
const counts = computed(() => {
  const all = list.value
  return {
    total: all.length,
    making: all.filter((i) => i.status === '制作中').length,
    pending: all.filter((i) => i.status === '待发布').length,
    published: all.filter((i) => i.status === '已完成').length
  }
})

const statCards = computed(() => [
  { label: '创作总量', value: counts.value.total, icon: VideoCamera, tone: 'blue' },
  { label: '制作中', value: counts.value.making, icon: Loading, tone: 'lilac' },
  { label: '待发布', value: counts.value.pending, icon: Timer, tone: 'amber' },
  { label: '已发布', value: counts.value.published, icon: CircleCheckFilled, tone: 'mint' }
])

const edit = reactive({
  visible: false, loading: false, saving: false, id: null,
  form: emptyEditForm()
})
const create = reactive({
  visible: false, loading: false, saving: false,
  form: emptyCreateForm()
})

function emptyCreateForm() {
  return {
    title: '', category_id: null, characterIds: [], platform: '',
    promptText: '', remark: ''
  }
}

function emptyEditForm() {
  return {
    title: '', cover: '', tags: [], douyin_url: '', category_id: null,
    characterIds: [], platform: '', promptText: '',
    owner_id: null, ownerName: '', status: '制作中', remark: ''
  }
}

// 分段提示词 → 单段文字（兼容历史数据：多段用换行拼接）
function promptToText(prompt) {
  if (!prompt || !prompt.length) return ''
  return prompt.map((p) => p.text || '').filter(Boolean).join('\n').slice(0, 2500)
}

function categoryName(id) {
  if (!id) return ''
  const c = settings.categoryOptions.find((x) => x.id === id)
  return c ? c.name : ''
}

// 新增制作：弹窗不展示封面/作者/创作人，保存时自动生成默认封面、当前登录作者与创作人、开始时间=提交时间
function openCreate() {
  Object.assign(create.form, emptyCreateForm())
  create.visible = true
}

async function doCreate() {
  const f = create.form
  if (!f.title.trim()) return ElMessage.warning('请填写视频名称')
  if (!f.category_id) return ElMessage.warning('请选择类型')
  if (!f.characterIds.length) return ElMessage.warning('请选择使用资产')
  if (!f.platform) return ElMessage.warning('请选择制作平台')
  if (!f.promptText.trim()) return ElMessage.warning('请填写提示词')
  create.saving = true
  try {
    const payload = {
      title: f.title.trim(),
      cover: '/placeholder.svg',
      author: auth.displayName,
      category_id: f.category_id,
      platform: f.platform,
      prompt: [{ seg: '', text: f.promptText.trim() }],
      status: '制作中',
      remark: f.remark,
      characters: f.characterIds.map((id, i) => ({ character_id: id, role: i === 0 ? '主角' : '配角', sort: i }))
    }
    await api.post('/productions', payload)
    ElMessage.success('创建成功，已进入制作中')
    create.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    create.saving = false
  }
}

// 客户端分页
const pagedList = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE.value
  return list.value.slice(start, start + PAGE_SIZE.value)
})

async function load() {
  loading.value = true
  try {
    // 展示全部创作记录，四项统计直接由当前可见范围计算
    const { data } = await api.get('/productions', {
      params: { keyword: keyword.value, platform: platform.value, scope: scope.value, page_size: 200 }
    })
    list.value = data.items || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败，请重试')
  } finally {
    loading.value = false
  }
}

async function loadCharacters() {
  try {
    const { data } = await api.get('/characters', { params: { scope: 'all' } })
    characterOptions.value = (data || []).filter((a) => (a.asset_type || 'character') === 'character')
  } catch (e) {
    characterOptions.value = []
  }
}

// 制作中/待发布状态可点击确认流转；已完成只读
function canChangeStatus(row) {
  return perm.can('productions.edit') && (row.is_owner || auth.isAdmin)
}

function statusClickTitle(row) {
  if (!canChangeStatus(row)) return '仅归属人或管理员可改'
  if (row.status === '制作中') return '点击确认完成并进入待发布'
  if (row.status === '待发布') return '点击确认还原为制作中'
  return productionStatusLabel(row.status)
}

// 制作中→待发布前的信息完整性校验：制作平台 + 提示词内容必填
function missingProductionInfo(row) {
  const missing = []
  if (!row.platform) missing.push('制作平台')
  const promptText = (row.prompt || []).map((p) => p.text || '').join('').trim()
  if (!promptText) missing.push('提示词')
  return missing
}

// 制作中点状态：校验信息完整后确认完成→待发布；待发布点状态：确认还原→制作中
function openStatusConfirm(row) {
  if (!canChangeStatus(row)) return
  if (row.status === '制作中') {
    const missing = missingProductionInfo(row)
    if (missing.length) {
      ElMessage.warning(`请先补全制作信息：${missing.join('、')}，再确认完成`)
      return
    }
    statusConfirm.target = '待发布'
    statusConfirm.title = '确认完成制作'
    statusConfirm.message = `确定「${row.title || '该视频'}」已完成制作吗？确认后状态更新为「待发布」。`
    statusConfirm.confirmText = '确认完成'
    statusConfirm.variant = 'success'
    statusConfirm.icon = 'success'
  } else if (row.status === '待发布') {
    statusConfirm.target = '制作中'
    statusConfirm.title = '还原为制作中'
    statusConfirm.message = `确定将「${row.title || '该视频'}」还原为「制作中」吗？`
    statusConfirm.confirmText = '确认还原'
    statusConfirm.variant = 'warning'
    statusConfirm.icon = 'warning'
  } else {
    return
  }
  statusConfirm.row = row
  statusConfirm.visible = true
}

async function doChangeStatus() {
  const row = statusConfirm.row
  if (!row) return
  statusConfirm.loading = true
  try {
    const { data } = await api.put(`/productions/${row.id}`, { status: statusConfirm.target })
    row.status = data.status
    row.produced_at = data.produced_at
    row.completed_at = data.completed_at
    ElMessage.success(`状态已改为「${data.status}」`)
    statusConfirm.visible = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '状态修改失败')
  } finally {
    statusConfirm.loading = false
  }
}

async function openEdit(row) {
  edit.id = row.id
  edit.loading = true
  edit.form = emptyEditForm()
  edit.visible = true
  try {
    const { data } = await api.get(`/productions/${row.id}`)
    Object.assign(edit.form, {
      title: data.title || '',
      cover: data.cover || '',
      tags: [...(data.tags || [])],
      douyin_url: data.douyin_url || '',
      category_id: data.category_id || null,
      characterIds: (data.characters || []).map((c) => c.character_id),
      platform: data.platform || '',
      promptText: promptToText(data.prompt),
      owner_id: data.owner_id || null,
      ownerName: data.owner_name || '未指定',
      status: data.status || '制作中',
      remark: data.remark || ''
    })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载详情失败')
  } finally {
    edit.loading = false
  }
}

async function doEdit() {
  edit.saving = true
  try {
    // 参考视频信息 / 制作人 / 状态均为只读，不再提交，仅保存可编辑的制作字段
    const payload = {
      platform: edit.form.platform,
      prompt: [{ seg: '', text: edit.form.promptText }],
      remark: edit.form.remark,
      characters: edit.form.characterIds.map((id, i) => ({ character_id: id, role: i === 0 ? '主角' : '配角', sort: i }))
    }
    await api.put(`/productions/${edit.id}`, payload)
    ElMessage.success('已保存')
    edit.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    edit.saving = false
  }
}

function remove(row) {
  confirm.title = '删除制作记录'
  confirm.message = `确定删除「${row.title || '未命名制作'}」吗？删除后无法恢复。`
  confirm.id = row.id
  confirm.visible = true
}

async function doRemove() {
  confirm.loading = true
  try {
    await api.delete(`/productions/${confirm.id}`)
    ElMessage.success('已删除')
    confirm.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    confirm.loading = false
  }
}

onMounted(async () => {
  await settings.load()
  await loadCharacters()
  load()
})
</script>

<style scoped>
/* 状态按钮：制作中/待发布可点击确认流转 */
.prod-status-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 4px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}
.prod-status-btn:hover:not(:disabled) {
  border-color: var(--el-color-primary-light-7, #d9ecff);
  background: var(--adm-blue-bg, #eef4ff);
}
.prod-status-btn:disabled { cursor: default; }

.char-cell { display: flex; align-items: center; gap: 5px; }
.char-avatar { width: 26px; height: 26px; border-radius: 9px; border: 1px solid rgba(123, 163, 209, 0.2); display: block; flex-shrink: 0; background: var(--adm-panel-soft); }
.char-names { font-size: 12.5px; color: var(--adm-text-secondary); overflow: hidden; display: -webkit-box; -webkit-box-orient: vertical; -webkit-line-clamp: 2; word-break: break-word; }

/* 创作时间：开始 / 完成上下两行，图标区分 */
.prod-time-cell { display: flex; flex-direction: column; gap: 3px; width: 100%; }
.prod-time-row { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--adm-text-secondary); }
.prod-time-row.is-start .el-icon { color: #409eff; }
.prod-time-row.is-done .el-icon { color: #3da377; }
.prod-time-row > span:first-of-type { color: var(--adm-text-tertiary); }
.prod-time-row .adm-cell-time { font-size: 11px; }

/* 视频名称第二行：作者 + 类别（复刻创意灵感） */
.idea-author { color: var(--adm-text-secondary); margin-right: 6px; }
/* 话题标签：最多两行换行显示（与创意灵感一致） */
.idea-tags { max-height: 56px; overflow: hidden; }

/* 编辑弹窗：沿用全局公共弹窗视觉令牌，仅补充表单区布局 */
/* 弹窗限高与 flex 布局见 style.css 的 .edit-dialog.el-dialog 全局规则 */
.edit-dialog-body { padding: 4px 2px; height: 100%; overflow-y: auto; }
.edit-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 4px 4px;
  margin-top: 6px;
}
/* 底部按钮统一样式：胶囊、同高、主色系 */
.edit-dialog-footer .el-button {
  min-width: 84px;
  border-radius: 999px;
  font-weight: 600;
}
/* 只读项：类型 / 制作人 / 状态，横向排列在参考视频卡片内，无小标题 */
.readonly-row { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.readonly-item { display: inline-flex; align-items: center; }
.edit-dialog :deep(.adm-drawer-section) { margin-bottom: 4px; }
.edit-dialog :deep(.el-form-item) { margin-bottom: 14px; }
/* 参考视频：只读展示（封面 + 可点击标题 / 标签），抖音链接不再单独显示 */
.ref-video-view {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--adm-border);
  border-radius: 10px;
  background: var(--adm-panel-soft, #f8fafc);
}
.ref-cover {
  width: 92px;
  height: 92px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid var(--adm-border);
  background: var(--adm-panel);
}
.ref-cover.is-empty { opacity: 0.6; }
/* 新建弹窗：封面默认图 + 作者/创作人只读提示 */
/* 右侧三行（标题 / 标签 / 只读项）与左侧 92px 封面等高，垂直方向平分对齐 */
.ref-video-info {
  display: flex;
  flex-direction: column;
  justify-content: space-around;
  height: 92px;
  min-width: 0;
  flex: 1;
}
.ref-title { font-size: 14px; font-weight: 600; color: var(--adm-text-primary); line-height: 1.4; }
.ref-tags { display: flex; flex-wrap: wrap; gap: 4px; }
.ref-title-link { text-decoration: none; cursor: pointer; }
.ref-title-link:hover { text-decoration: underline; color: var(--el-color-primary); }
.prompt-textarea { width: 100%; }
</style>
