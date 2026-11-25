<template>
  <div class="stack">
    <PageHeader :icon="Connection" title="我的账号" tone="coral" desc="第五步 · 视频实际发布的平台账号，维护账号资料、标签与数据指标">
      <template #extra>
        <el-input
          v-model="keyword"
          placeholder="搜索账号名称 / ID / 备注"
          clearable
          style="width: 190px"
          @keyup.enter="load"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="platform" placeholder="全部平台" clearable style="width: 120px" @change="load">
          <el-option v-for="p in publishPlatformOptions" :key="p.name" :label="p.name" :value="p.name">
            <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
          </el-option>
        </el-select>
        <el-select v-model="scope" style="width: 120px" @change="load">
          <el-option label="全部数据" value="all" />
          <el-option label="仅看我的" value="mine" />
        </el-select>
        <el-dropdown trigger="click" @command="onAddCommand">
          <el-button type="primary" :icon="Plus" :loading="loggingId !== null || scanning">
            添加账号<el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </el-button>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item command="manual">手动添加</el-dropdown-item>
              <el-dropdown-item command="douyin" divided>抖音扫码登录</el-dropdown-item>
              <el-dropdown-item command="video">视频扫码添加</el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
    </PageHeader>

    <!-- 统计 -->
    <div class="stat-row">
      <StatCard tone="coral" :icon="Connection" label="账号总数" :value="total" sub-label="独立管理的发布账号" />
      <StatCard tone="blue" :icon="VideoCamera" label="视频数量" :value="sumVideoCount" sub-label="各账号作品数合计" />
      <StatCard tone="amber" :icon="Star" label="累计获赞" :value="sumLikesCount" sub-label="各账号获赞合计" />
      <StatCard tone="mint" :icon="UserFilled" label="粉丝总数" :value="sumFollowersCount" sub-label="各账号粉丝合计" />
    </div>

    <!-- 账号列表 -->
    <el-card shadow="never" class="adm-card adm-card--table" :class="{ 'is-loading': loading }">
      <GridSkeleton v-if="loading" :rows="8" :cols="6" />
      <div class="adm-table-wrap">
        <el-table :data="pagedList" stripe style="width: 100%">
          <el-table-column label="头像" width="72" align="center">
            <template #default="{ row }">
              <div class="adm-cell-cover">
                <el-image
                  v-if="row.avatar"
                  :src="row.avatar"
                  :preview-src-list="[row.avatar]"
                  preview-teleported
                  fit="cover"
                  class="account-avatar-img"
                  :alt="row.name"
                />
                <div v-else class="account-avatar-img is-empty"><el-icon :size="16"><UserFilled /></el-icon></div>
              </div>
            </template>
          </el-table-column>

          <!-- 账号数据：名称在上，账号 ID + 复制图标在下 -->
          <el-table-column label="账号名称" min-width="158" align="left">
            <template #default="{ row }">
              <div class="account-name-cell">
                <span class="adm-cell-text adm-cell-text--clamp2" :title="row.name">{{ row.name }}</span>
                <div class="account-id-line">
                  <span class="account-id-text" :title="row.account_id || row.douyin_uid">{{ row.account_id || row.douyin_uid || '—' }}</span>
                  <el-button
                    v-if="row.account_id || row.douyin_uid"
                    link
                    class="copy-id-btn"
                    :icon="CopyDocument"
                    title="复制账号 ID"
                    @click="copyAccountId(row)"
                  />
                </div>
              </div>
            </template>
          </el-table-column>

          <!-- 状态：只区分在线 / 离线，点击可重新扫码 -->
          <el-table-column label="状态" min-width="90" align="center">
            <template #default="{ row }">
              <el-tooltip
                :content="`点击扫码登录${row.douyin_login_at ? `｜登录于 ${formatDateTime(row.douyin_login_at)}` : ''}`"
                placement="top"
              >
                <el-tag
                  :type="onlineStatusType(row)"
                  size="small"
                  effect="light"
                  class="login-status-tag"
                  @click="loginAccount(row)"
                >{{ onlineLabel(row) }}</el-tag>
              </el-tooltip>
            </template>
          </el-table-column>

          <el-table-column label="平台" min-width="96" align="center">
            <template #default="{ row }">
              <OptionBadge
                v-if="row.platform"
                :name="row.platform"
                :color="settings.option('publish', row.platform).color"
                :image="settings.option('publish', row.platform).image"
                :display="settings.option('publish', row.platform).display"
              />
              <span v-else class="adm-cell-empty">未标注</span>
            </template>
          </el-table-column>

          <el-table-column label="作品数量" min-width="104" align="right">
            <template #default="{ row }">
              <span class="delta-value">
                <span class="adm-cell-num">{{ row.video_count || 0 }}</span>
                <span v-if="deltaOf(row, 'video_count') !== null" class="delta-badge" :class="deltaClass(deltaOf(row, 'video_count'))">
                  {{ deltaText(deltaOf(row, 'video_count')) }}
                </span>
              </span>
            </template>
          </el-table-column>

          <el-table-column label="获赞" min-width="108" align="right">
            <template #default="{ row }">
              <span class="delta-value">
                <span class="adm-cell-num">{{ formatCount(row.likes_count) }}</span>
                <span v-if="deltaOf(row, 'likes_count') !== null" class="delta-badge" :class="deltaClass(deltaOf(row, 'likes_count'))">
                  {{ deltaText(deltaOf(row, 'likes_count')) }}
                </span>
              </span>
            </template>
          </el-table-column>

          <el-table-column label="粉丝" min-width="108" align="right">
            <template #default="{ row }">
              <span class="delta-value">
                <span class="adm-cell-num">{{ formatCount(row.followers_count) }}</span>
                <span v-if="deltaOf(row, 'followers_count') !== null" class="delta-badge" :class="deltaClass(deltaOf(row, 'followers_count'))">
                  {{ deltaText(deltaOf(row, 'followers_count')) }}
                </span>
              </span>
            </template>
          </el-table-column>

          <!-- 运营管理：更新节奏 / 责任人，上下两行标签，点击即可选择 -->
          <el-table-column label="运营管理" min-width="132" align="left">
            <template #default="{ row }">
              <div class="rhythm-owner-cell">
                <el-dropdown trigger="click" @command="(v) => patchAccount(row, { update_rhythm: v })">
                  <span class="management-tag-wrap">
                    <el-tag size="small" effect="light" class="management-tag">{{ row.update_rhythm || '日更' }}</el-tag>
                  </span>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="r in UPDATE_RHYTHM_OPTIONS"
                        :key="r"
                        :command="r"
                        :disabled="r === (row.update_rhythm || '日更')"
                      >{{ r }}</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
                <el-dropdown trigger="click" @command="(v) => patchAccount(row, { responsible_id: v || null })">
                  <span class="management-tag-wrap">
                    <el-tag size="small" effect="plain" class="management-tag">
                      {{ row.responsible_name || '未指定' }}
                    </el-tag>
                  </span>
                  <template #dropdown>
                    <el-dropdown-menu>
                      <el-dropdown-item
                        v-for="c in creatorOptions"
                        :key="c.id"
                        :command="c.id"
                        :disabled="c.id === row.responsible_id"
                      >{{ c.display_name }}</el-dropdown-item>
                      <el-dropdown-item v-if="row.responsible_id" command="" divided>清除责任人</el-dropdown-item>
                    </el-dropdown-menu>
                  </template>
                </el-dropdown>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="备注" min-width="132" align="left">
            <template #default="{ row }">
              <div class="note-cell" :class="{ 'is-editing': editingNoteId === row.id }">
                <el-input
                  v-if="editingNoteId === row.id"
                  v-model="editingNote"
                  type="textarea"
                  :rows="2"
                  resize="none"
                  maxlength="200"
                  class="note-input"
                  placeholder="填写备注"
                  @click.stop
                />
                <el-tooltip
                  v-else
                  :content="row.note || '点击填写备注'"
                  popper-class="note-tooltip"
                  placement="top"
                  :disabled="!row.note"
                >
                  <div class="note-text" @click.stop="startNoteEdit(row)">{{ row.note || '点击填写备注' }}</div>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" min-width="158" align="center" fixed="right">
            <template #default="{ row }">
              <div class="adm-cell-actions">
                <el-button
                  type="text"
                  size="small"
                  :icon="Clock"
                  @click="openSnapshots(row)"
                >快照</el-button>
                <el-button
                  type="text"
                  size="small"
                  :loading="updatingId === row.id"
                  @click="updateAccount(row)"
                >更新</el-button>
                <el-button
                  v-if="perm.can('publish-accounts.delete')"
                  type="text"
                  size="small"
                  class="danger-text"
                  @click="askRemove(row)"
                >删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :image-size="100" description="还没有发布账号，点右上角「添加账号」" />
          </template>
        </el-table>
      </div>

      <AppPagination
        v-model:page="page"
        v-model:page-size="pageSize"
        :total="filteredList.length"
      />
    </el-card>

    <!-- 手动添加账号 -->
    <el-dialog v-model="manualVisible" title="手动添加账号" width="480px" class="edit-dialog" destroy-on-close>
      <div class="manual-form">
        <el-form label-width="92px">
          <el-form-item label="账号名称" required>
            <el-input v-model="manualForm.name" placeholder="请输入账号名称" maxlength="100" />
          </el-form-item>
          <el-form-item label="发布平台">
            <el-select v-model="manualForm.platform" style="width: 100%">
              <el-option v-for="p in publishPlatformOptions" :key="p.name" :label="p.name" :value="p.name" />
            </el-select>
          </el-form-item>
          <el-form-item label="平台账号 ID">
            <el-input v-model="manualForm.account_id" placeholder="选填，如抖音号 / 平台账号" />
          </el-form-item>
          <el-form-item label="更新节奏">
            <el-select v-model="manualForm.update_rhythm" style="width: 100%">
              <el-option v-for="r in UPDATE_RHYTHM_OPTIONS" :key="r" :value="r" :label="r" />
            </el-select>
          </el-form-item>
          <el-form-item label="备注">
            <el-input v-model="manualForm.note" type="textarea" :rows="2" placeholder="选填" />
          </el-form-item>
        </el-form>
      </div>
      <div class="edit-dialog-footer">
        <el-button @click="manualVisible = false">取消</el-button>
        <el-button type="primary" :loading="manualSaving" @click="doManualCreate">添加</el-button>
      </div>
    </el-dialog>

    <!-- 历史快照：每次更新后的作品数 / 获赞 / 粉丝等指标 -->
    <el-dialog v-model="snapshotVisible" title="历史快照" width="760px" class="edit-dialog snapshot-dialog" destroy-on-close>
      <div class="snapshot-sub">账号「{{ snapshotAccount?.name || '' }}」每次更新后的资料数据；发布数据作品的播放数据不写入这里</div>
      <el-table
        :data="snapshots"
        stripe
        size="small"
        v-loading="snapshotLoading"
        empty-text="暂无历史快照，执行自动更新或点击「更新」后生成"
        max-height="420"
      >
        <el-table-column label="快照时间" min-width="150" align="right">
          <template #default="{ row }">
            <span class="adm-cell-time">{{ formatDateTime(row.snapshot_at) }}</span>
          </template>
        </el-table-column>
        <el-table-column label="作品数量" min-width="96" align="right">
          <template #default="{ row }"><span class="adm-cell-num">{{ row.video_count || 0 }}</span></template>
        </el-table-column>
        <el-table-column label="获赞" min-width="96" align="right">
          <template #default="{ row }"><span class="adm-cell-num">{{ formatCount(row.likes_count) }}</span></template>
        </el-table-column>
        <el-table-column label="粉丝" min-width="96" align="right">
          <template #default="{ row }"><span class="adm-cell-num">{{ formatCount(row.followers_count) }}</span></template>
        </el-table-column>
        <el-table-column label="采集作品" min-width="100" align="right">
          <template #default="{ row }"><span class="adm-cell-num">{{ row.fetched_video_count || 0 }}</span></template>
        </el-table-column>
        <el-table-column label="来源" min-width="90" align="center">
          <template #default="{ row }">
            <el-tag size="small" effect="plain">{{ row.source === 'auto' ? '自动' : '手动' }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="备注" min-width="150" align="left">
          <template #default="{ row }">
            <span class="adm-cell-sub">{{ row.note || '—' }}</span>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="snapshotVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 视频扫码添加：摄像头识别二维码 → 解析视频作者建号 -->
    <el-dialog v-model="scanVisible" title="视频扫码添加" width="560px" class="edit-dialog" destroy-on-close @closed="stopScan">
      <div class="scan-body">
        <div class="scan-tip">用摄像头对准抖音视频二维码，或手动粘贴视频链接；识别后自动解析作者并建号。</div>
        <div class="scan-video-wrap">
          <video ref="scanVideoRef" class="scan-video" playsinline muted></video>
          <canvas ref="scanCanvasRef" class="scan-canvas"></canvas>
          <div v-if="!scanStream" class="scan-placeholder">
            <el-icon :size="34"><Camera /></el-icon>
            <span>点击下方按钮打开摄像头</span>
          </div>
          <div v-if="scanFound" class="scan-corner">已识别二维码</div>
        </div>
        <div class="scan-actions">
          <el-button v-if="!scanStream" :icon="Camera" @click="startScan">打开摄像头</el-button>
          <el-button v-else @click="stopScan">关闭摄像头</el-button>
          <span class="scan-or">或粘贴链接</span>
        </div>
        <el-input v-model="scanUrl" placeholder="https://v.douyin.com/... 或抖音视频链接" clearable />
        <div v-if="scanResult" class="scan-result">
          <el-icon><CircleCheckFilled /></el-icon>
          {{ scanResult }}
        </div>
      </div>
      <div class="edit-dialog-footer">
        <el-button @click="scanVisible = false">取消</el-button>
        <el-button type="primary" :loading="scanning" :disabled="!scanUrl" @click="doVideoCreate">解析并添加</el-button>
      </div>
    </el-dialog>

    <!-- 远程扫码：服务端无头浏览器抓二维码回传，局域网用户直接扫页面 -->
    <el-dialog
      v-model="qrVisible"
      title="抖音扫码登录"
      width="430px"
      class="edit-dialog"
      :close-on-click-modal="false"
      destroy-on-close
      @closed="cancelQrLogin"
    >
      <div class="remote-qr-body">
        <div v-if="qrImage" class="remote-qr-image-wrap">
          <img :src="qrImage" class="remote-qr-image" alt="抖音登录二维码" />
          <div v-if="qrKind === 'page'" class="remote-qr-warning">
            未能自动定位二维码元素，当前显示登录页截图；请按页面提示操作，或改用手动添加
          </div>
        </div>
        <div v-else class="remote-qr-loading">
          <el-icon class="is-loading"><Connection /></el-icon>
          <span>{{ qrMessage || '正在打开抖音登录页…' }}</span>
        </div>
        <div class="remote-qr-status">{{ qrMessage }}</div>
        <div class="remote-qr-hint">
          请用手机抖音 App 扫描上方二维码。登录态保存在服务器上，扫码成功后本窗口会自动关闭。
        </div>
      </div>
    </el-dialog>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="confirmVisible"
      title="删除发布账号"
      :message="`确定删除账号「${removing?.name || ''}」吗？删除后不可恢复。`"
      confirm-text="确认删除"
      @confirm="doRemove"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, onUnmounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  ArrowDown, Camera, CircleCheckFilled, Clock, Connection, CopyDocument,
  Plus, Search, Star, UserFilled, VideoCamera
} from '@element-plus/icons-vue'
import jsQR from 'jsqr'
import PageHeader from '../components/PageHeader.vue'
import AppPagination from '../components/ui/AppPagination.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import OptionBadge from '../components/ui/OptionBadge.vue'
import StatCard from '../components/ui/StatCard.vue'
import { usePermissionStore } from '../stores/permission'
import { useSettingsStore } from '../stores/settings'
import {
  api, UPDATE_RHYTHM_OPTIONS, formatDateTime
} from '../api'

const perm = usePermissionStore()
const settings = useSettingsStore()
const loading = ref(false)
const list = ref([])
const keyword = ref('')
const platform = ref('')
const scope = ref('all')
const page = ref(1)
const pageSize = ref(10)

const confirmVisible = ref(false)
const removing = ref(null)
const creatorOptions = ref([])
const loggingId = ref(null)       // 扫码登录中（null 表示空闲）
const qrVisible = ref(false)
const qrSession = ref('')
const qrImage = ref('')
const qrSeq = ref(0)
const qrKind = ref('qr')
const qrMessage = ref('')
const qrTimer = ref(null)
const updatingId = ref(null)      // 行内更新中
const snapshotVisible = ref(false)
const snapshotLoading = ref(false)
const snapshotAccount = ref(null)
const snapshots = ref([])
const editingNoteId = ref(null)   // 备注行内编辑中的账号
const editingNote = ref('')

// 手动添加
const manualVisible = ref(false)
const manualSaving = ref(false)
const manualForm = ref({ name: '', platform: '抖音', account_id: '', update_rhythm: '日更', note: '' })

// 视频扫码添加
const scanVisible = ref(false)
const scanning = ref(false)
const scanUrl = ref('')
const scanFound = ref(false)
const scanResult = ref('')
const scanStream = ref(null)
const scanVideoRef = ref(null)
const scanCanvasRef = ref(null)
let scanRaf = null

function isDouyinAccount(row) {
  const pf = String(row.platform || '')
  return pf.includes('抖音') || !!(row.douyin_uid || row.home_url)
}

// 状态只看在线 / 离线：抖音账号看登录态，其他账号看业务状态
function isOnline(row) {
  if (isDouyinAccount(row)) return row.douyin_login_status === '已登录'
  return (row.status || '正常') === '正常'
}

function onlineStatusType(row) {
  return isOnline(row) ? 'success' : 'danger'
}

function onlineLabel(row) {
  return isOnline(row) ? '在线' : '离线'
}

const total = computed(() => filteredList.value.length)
const sumVideoCount = computed(() => filteredList.value.reduce((s, a) => s + (a.video_count || 0), 0))
const sumLikesCount = computed(() => filteredList.value.reduce((s, a) => s + (a.likes_count || 0), 0))
const sumFollowersCount = computed(() => filteredList.value.reduce((s, a) => s + (a.followers_count || 0), 0))

// 发布平台选项优先取配置中心（含颜色 / 图片 / 展示方式），并保留账号里已有的自定义平台
const publishPlatformOptions = computed(() => {
  const configured = settings.publishPlatformOptions.map((p) => ({ ...p }))
  const known = new Set(configured.map((p) => p.name))
  list.value.forEach((a) => {
    if (a.platform && !known.has(a.platform)) {
      known.add(a.platform)
      configured.push(settings.option('publish', a.platform))
    }
  })
  return configured
})

const filteredList = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  return list.value.filter((a) => {
    if (platform.value && a.platform !== platform.value) return false
    if (!kw) return true
    return [a.name, a.account_id, a.douyin_uid, a.note].some((v) => String(v || '').toLowerCase().includes(kw))
  })
})

const pagedList = computed(() => {
  const start = (page.value - 1) * pageSize.value
  return filteredList.value.slice(start, start + pageSize.value)
})

function formatCount(n) {
  const v = Number(n || 0)
  if (v >= 100000000) return (v / 100000000).toFixed(1).replace(/\.0$/, '') + ' 亿'
  if (v >= 10000) return (v / 10000).toFixed(1).replace(/\.0$/, '') + ' 万'
  return String(v)
}

// 相对上一次采集的增量；无历史快照或增量为 0 时返回 null，不显示角标
function deltaOf(row, key) {
  const d = row?.deltas
  if (!d || d[key] === undefined || d[key] === null) return null
  const v = Number(d[key])
  if (!Number.isFinite(v) || v === 0) return null
  return v
}

function deltaText(v) {
  if (v === null) return ''
  const sign = v > 0 ? '+' : v < 0 ? '-' : ''
  return sign + formatCount(Math.abs(v))
}

function deltaClass(v) {
  if (v === null || v === 0) return ''
  return v > 0 ? 'is-up' : 'is-down'
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/publish-accounts', { params: { scope: scope.value } })
    list.value = Array.isArray(data) ? data : []
  } catch (e) {
    list.value = []
    ElMessage.error(e.response?.data?.detail || '加载失败')
  } finally {
    loading.value = false
  }
}

// 添加账号入口：三种方式
function onAddCommand(cmd) {
  if (cmd === 'manual') {
    manualForm.value = { name: '', platform: '抖音', account_id: '', update_rhythm: '日更', note: '' }
    manualVisible.value = true
  } else if (cmd === 'douyin') {
    loginNewAccount()
  } else if (cmd === 'video') {
    scanUrl.value = ''
    scanFound.value = false
    scanResult.value = ''
    scanVisible.value = true
    nextTick(() => startScan())
  }
}

// 手动添加：直接建号
async function doManualCreate() {
  if (!manualForm.value.name.trim()) {
    ElMessage.warning('请输入账号名称')
    return
  }
  manualSaving.value = true
  try {
    await api.post('/publish-accounts', {
      name: manualForm.value.name.trim(),
      platform: manualForm.value.platform,
      account_id: manualForm.value.account_id.trim(),
      update_rhythm: manualForm.value.update_rhythm,
      note: manualForm.value.note.trim(),
    })
    ElMessage.success('账号已添加')
    manualVisible.value = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '添加失败')
  } finally {
    manualSaving.value = false
  }
}

// 摄像头扫码：逐帧用 jsQR 识别二维码
async function startScan() {
  if (scanStream.value) return
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { facingMode: { ideal: 'environment' } }, audio: false,
    })
    scanStream.value = stream
    await nextTick()
    const video = scanVideoRef.value
    if (!video) return
    video.srcObject = stream
    await video.play()
    scanLoop()
  } catch (e) {
    ElMessage.warning('无法打开摄像头，请检查浏览器摄像头权限，或手动粘贴视频链接')
  }
}

function scanLoop() {
  const video = scanVideoRef.value
  const canvas = scanCanvasRef.value
  if (!video || !canvas || !scanStream.value) return
  if (video.readyState >= 2) {
    const w = video.videoWidth
    const h = video.videoHeight
    if (w && h) {
      canvas.width = w
      canvas.height = h
      const ctx = canvas.getContext('2d', { willReadFrequently: true })
      ctx.drawImage(video, 0, 0, w, h)
      const image = ctx.getImageData(0, 0, w, h)
      const code = jsQR(image.data, w, h, { inversionAttempts: 'attemptBoth' })
      if (code && code.data) {
        scanUrl.value = code.data.trim()
        scanFound.value = true
        stopScan()
        ElMessage.success('已识别二维码链接，点「解析并添加」继续')
        return
      }
    }
  }
  scanRaf = requestAnimationFrame(scanLoop)
}

function stopScan() {
  if (scanRaf) {
    cancelAnimationFrame(scanRaf)
    scanRaf = null
  }
  if (scanStream.value) {
    scanStream.value.getTracks().forEach((t) => t.stop())
    scanStream.value = null
  }
}

// 视频链接 → 解析作者建号
async function doVideoCreate() {
  if (!scanUrl.value.trim()) {
    ElMessage.warning('请扫码或粘贴视频链接')
    return
  }
  scanning.value = true
  scanResult.value = ''
  try {
    const { data } = await api.post('/douyin/account/from-video', { url: scanUrl.value.trim() }, { timeout: 180000 })
    if (!data.ok) {
      if (data.need_login) {
        await ElMessageBox.alert(
          `${data.message || '需要抖音验证'}｜请先用「抖音扫码登录」完成验证，或改用手动添加。`,
          '需要抖音验证',
          { confirmButtonText: '知道了' },
        ).catch(() => {})
      } else {
        ElMessage.warning(data.message || '解析失败，请改用手动添加')
      }
      return
    }
    scanResult.value = `${data.created ? '已新建' : '已回填'}账号「${data.account_name}」`
    ElMessage.success(data.created ? '已从视频作者新建账号' : '该作者账号已存在，已回填')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '解析失败')
  } finally {
    scanning.value = false
  }
}

// 远程扫码：后端无头浏览器抓二维码，前端弹窗展示并轮询结果
function clearQrTimer() {
  if (qrTimer.value) {
    clearInterval(qrTimer.value)
    qrTimer.value = null
  }
}

async function cancelQrLogin() {
  clearQrTimer()
  const session = qrSession.value
  qrSession.value = ''
  qrImage.value = ''
  if (session) {
    try { await api.post('/douyin/login/cancel', { session }) } catch (_) { /* 忽略 */ }
  }
}

async function startRemoteLogin(accountId) {
  clearQrTimer()
  qrImage.value = ''
  qrSeq.value = 0
  qrKind.value = 'qr'
  qrMessage.value = '正在打开抖音登录页（首次加载约需半分钟），请稍候…'
  qrVisible.value = true
  try {
    const { data } = await api.post('/douyin/login/start', accountId ? { account_id: accountId } : {})
    if (!data.ok) throw new Error(data.message || '启动扫码失败')
    qrSession.value = data.session
  } catch (e) {
    qrVisible.value = false
    ElMessage.error(e.response?.data?.detail || e.message || '启动扫码失败')
    return
  }
  qrTimer.value = setInterval(pollRemoteLogin, 1200)
  pollRemoteLogin()
}

async function pollRemoteLogin() {
  const session = qrSession.value
  if (!session || !qrVisible.value) {
    clearQrTimer()
    return
  }
  try {
    const { data } = await api.get('/douyin/login/status', { params: { session, qr_seq: qrSeq.value } })
    if (data.qr) {
      qrImage.value = data.qr
      qrSeq.value = Number(data.qr_seq || 0)
    }
    qrKind.value = data.kind || 'qr'
    qrMessage.value = data.message || ''
    if (data.status === 'success') {
      clearQrTimer()
      qrVisible.value = false
      const result = data.result || {}
      ElMessage.success(result.created ? '扫码成功，已新建账号' : `扫码成功，已更新账号「${result.account_name || ''}」`)
      qrSession.value = ''
      await load()
      return
    }
    if (data.status === 'failed') {
      clearQrTimer()
      qrVisible.value = false
      ElMessage.warning({
        message: [data.message || '扫码失败', data.manual_hint].filter(Boolean).join('｜'),
        duration: 8000,
      })
      qrSession.value = ''
    }
  } catch (e) {
    clearQrTimer()
    qrVisible.value = false
    ElMessage.error(e.response?.data?.detail || '扫码状态查询失败')
  }
}

// 抖音扫码登录：后端按登录用户自动建号或回填已有账号
async function loginNewAccount() {
  if (loggingId.value !== null) return
  loggingId.value = -1
  try {
    await startRemoteLogin()
  } finally {
    loggingId.value = null
  }
}

// 表格内点击登录状态：用该账号自己的登录态重新扫码
async function loginAccount(row) {
  if (loggingId.value !== null) return
  loggingId.value = row.id
  try {
    await startRemoteLogin(row.id)
  } finally {
    loggingId.value = null
  }
}

async function copyAccountId(row) {
  const text = String(row.account_id || row.douyin_uid || '')
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage.success('账号 ID 已复制')
  } catch (_) {
    ElMessage.info(`账号 ID：${text}`)
  }
}

// 备注：点击单元格出现两行文本域，点击空白处保存
function startNoteEdit(row) {
  if (editingNoteId.value === row.id) return
  if (editingNoteId.value) saveNoteEdit()
  if (!perm.can('publish-accounts.edit')) {
    ElMessage.warning('没有编辑权限')
    return
  }
  editingNoteId.value = row.id
  editingNote.value = row.note || ''
  nextTick(() => {
    document.querySelector('.note-cell.is-editing textarea')?.focus()
  })
}

function saveNoteEdit() {
  const id = editingNoteId.value
  if (!id) return
  const row = list.value.find((x) => x.id === id)
  editingNoteId.value = null
  if (!row) return
  const note = editingNote.value || ''
  if ((row.note || '') === note) return
  patchAccount(row, { note })
}

function onDocClick(event) {
  if (!editingNoteId.value) return
  const editingCell = document.querySelector('.note-cell.is-editing')
  if (editingCell && editingCell.contains(event.target)) return
  saveNoteEdit()
}

// 表格内行编辑：更新节奏 / 责任人，改后即保存
async function patchAccount(row, patch) {
  if (!perm.can('publish-accounts.edit')) {
    ElMessage.warning('没有编辑权限')
    await load()
    return
  }
  const before = { update_rhythm: row.update_rhythm, responsible_id: row.responsible_id }
  Object.assign(row, patch)
  try {
    await api.put(`/publish-accounts/${row.id}`, patch)
    ElMessage.success('已保存')
  } catch (e) {
    Object.assign(row, before)
    ElMessage.error(e.response?.data?.detail || '保存失败')
    await load()
  }
}

// 历史快照：查看每次更新后的作品数量 / 获赞 / 粉丝
async function openSnapshots(row) {
  snapshotAccount.value = row
  snapshotVisible.value = true
  snapshotLoading.value = true
  snapshots.value = []
  try {
    const { data } = await api.get('/auto-update/snapshots', {
      params: { account_id: row.id, limit: 100 }
    })
    snapshots.value = Array.isArray(data) ? data : []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '快照加载失败')
  } finally {
    snapshotLoading.value = false
  }
}

// 单账号更新：总入口——同时更新账号资料与发布数据（采集条数取配置中心）
async function updateAccount(row) {
  updatingId.value = row.id
  try {
    const { data } = await api.post('/douyin/account/sync-one', { account_id: row.id }, { timeout: 180000 })
    if (!data.ok) {
      if (data.need_login) {
        await ElMessageBox.alert(
          `${data.message || '登录态已失效'}｜请点击该账号状态的离线标签重新扫码，再点更新。`,
          '需要抖音验证',
          { confirmButtonText: '知道了' }
        ).catch(() => {})
      } else {
        ElMessage.warning(data.message || '更新失败')
      }
    } else {
      const vc = Number(data.videos_created || 0)
      const vu = Number(data.videos_updated || 0)
      ElMessage.success(`账号数据已更新；发布数据新增 ${vc} 条、更新 ${vu} 条`)
    }
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '更新失败')
  } finally {
    updatingId.value = null
  }
}

function askRemove(row) {
  removing.value = row
  confirmVisible.value = true
}

async function doRemove() {
  if (!removing.value) return
  try {
    await api.delete(`/publish-accounts/${removing.value.id}`)
    ElMessage.success('账号已删除')
    confirmVisible.value = false
    removing.value = null
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function loadCreators() {
  try {
    const { data } = await api.get('/publish-accounts/creators')
    creatorOptions.value = Array.isArray(data) ? data : []
  } catch (e) {
    creatorOptions.value = []
  }
}

onMounted(async () => {
  await settings.load()
  await loadCreators()
  load()
  document.addEventListener('click', onDocClick)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  clearQrTimer()
})
</script>

<style scoped>
.account-name-cell { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.account-id-line { display: flex; align-items: center; gap: 2px; min-width: 0; }
.account-id-text {
  font-size: 11px;
  color: var(--adm-text-placeholder);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.copy-id-btn { padding: 2px; height: auto; font-size: 12px; color: var(--adm-text-secondary); }
.copy-id-btn:hover { color: var(--el-color-primary); }
.login-status-tag { cursor: pointer; min-width: 44px; }
/* 账号数据：数值右上角显示相对上次采集的增减（红涨绿跌） */
.delta-value { position: relative; display: inline-block; padding-right: 20px; }
.delta-badge {
  position: absolute;
  top: -6px;
  right: -2px;
  font-size: 10px;
  line-height: 1;
  font-weight: 600;
  white-space: nowrap;
}
.delta-badge.is-up { color: #e05252; }
.delta-badge.is-down { color: #1fa463; }
/* 运营管理：更新节奏 / 责任人上下两行标签 */
.rhythm-owner-cell { display: flex; flex-direction: column; align-items: flex-start; gap: 5px; }
.management-tag-wrap { display: inline-flex; cursor: pointer; width: 84px; }
.management-tag { width: 100%; justify-content: center; }
.management-tag :deep(.el-tag__content) {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
/* 头像：表格内放大显示，点击可预览大图 */
.account-avatar-img {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  overflow: hidden;
  cursor: zoom-in;
  background: var(--adm-surface-sunken);
  border: 1px solid var(--adm-border);
  transition: transform 0.18s ease, box-shadow 0.18s ease;
}
.account-avatar-img:hover {
  transform: scale(1.12);
  box-shadow: 0 3px 10px rgba(15, 23, 42, 0.16);
}
.account-avatar-img :deep(img) { width: 100%; height: 100%; object-fit: cover; display: block; }
.account-avatar-img.is-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--adm-text-placeholder);
  cursor: default;
}
/* 备注：两行截断，点击编辑，空白处保存 */
.note-cell { min-width: 0; }
.note-text {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  word-break: break-word;
  line-height: 1.45;
  min-height: 20px;
  font-size: 12.5px;
  color: var(--adm-text-primary);
  cursor: text;
  transition: color 0.15s ease;
}
.note-text:hover { color: var(--el-color-primary); }
.note-input { width: 100%; }
.note-input :deep(.el-textarea__inner) {
  padding: 5px 7px;
  line-height: 1.45;
  font-size: 12.5px;
  min-height: 44px !important;
  box-shadow: 0 0 0 1px var(--el-color-primary) inset;
}
.remote-qr-body {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 4px 0 8px;
}
.remote-qr-image-wrap {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}
.remote-qr-image {
  width: 240px;
  height: 240px;
  object-fit: contain;
  border: 1px solid var(--el-border-color-lighter);
  border-radius: 8px;
  background: #fff;
}
.remote-qr-warning {
  max-width: 320px;
  font-size: 12px;
  line-height: 1.6;
  color: var(--el-color-warning);
  text-align: center;
}
.remote-qr-loading {
  min-height: 240px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--adm-text-secondary);
  font-size: 13px;
}
.remote-qr-status { font-size: 13px; color: var(--adm-text-main, #334155); }
.remote-qr-hint {
  max-width: 340px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--adm-text-secondary);
  text-align: center;
}
</style>

<style>
/* 弹窗 teleport 到 body，样式需全局 */
.note-tooltip {
  max-width: 340px;
  white-space: pre-line;
  line-height: 1.5;
}
.snapshot-dialog .snapshot-sub {
  margin-bottom: 12px;
  font-size: 12.5px;
  color: var(--adm-text-secondary);
  line-height: 1.6;
}
.edit-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px 20px 14px;
  border-top: 1px solid var(--el-border-color-lighter);
}
.manual-form { padding: 4px 6px 8px; }
.scan-body { display: flex; flex-direction: column; gap: 12px; }
.scan-tip { font-size: 12.5px; color: var(--adm-text-secondary); line-height: 1.6; }
.scan-video-wrap {
  position: relative;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: #0f1115;
  border-radius: 8px;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}
.scan-video { width: 100%; height: 100%; object-fit: cover; }
.scan-canvas { display: none; }
.scan-placeholder {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: #8a94a6;
  font-size: 12.5px;
}
.scan-corner {
  position: absolute;
  top: 10px;
  right: 10px;
  background: rgba(16, 185, 129, 0.92);
  color: #fff;
  font-size: 11.5px;
  padding: 3px 9px;
  border-radius: 12px;
}
.scan-actions { display: flex; align-items: center; gap: 10px; }
.scan-or { font-size: 12px; color: var(--adm-text-placeholder); }
.scan-result {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12.5px;
  color: var(--el-color-success);
}
</style>