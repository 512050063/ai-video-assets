<template>
  <div class="stack">
    <PageHeader
      :icon="FolderOpened"
      title="素材共享"
      tone="amber"
      :desc="`${libraries.length} 个素材库 · ${allMaterials.length} 个共享素材，团队可复用`"
    >
      <template #extra>
        <el-input v-model="keyword" placeholder="搜索素材名称" clearable style="width: 200px" @keyup.enter="reloadAll" @clear="reloadAll">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="scope" style="width: 120px" @change="reloadAll">
          <el-option value="all" label="全部成员" />
          <el-option value="mine" label="仅我的" />
        </el-select>
      </template>
    </PageHeader>

    <!-- 素材库标签栏：拖图片到某个库即上传到该库；拖素材卡片到某个库即移动 -->
    <el-card shadow="never" class="adm-card lib-bar-card">
      <div class="lib-head">
        <span class="lib-head-title">素材库</span>
        <span class="lib-head-tip">拖图片到库标签即可上传，拖素材卡片到其它库即可移动</span>
      </div>
      <div class="lib-tab-list">
        <button
          v-for="lib in libraries"
          :key="lib.id"
          type="button"
          class="lib-tab"
          :class="{ 'is-active': activeKey === String(lib.id), 'is-dropover': dropLib === String(lib.id) }"
          :style="libTabStyle(lib)"
          @click="selectLibrary(lib)"
          @dragenter.prevent="onLibDragEnter($event, lib)"
          @dragover.prevent="onLibDragOver($event, lib)"
          @dragleave.prevent="onLibDragLeave(lib)"
          @drop.prevent="onLibDrop($event, lib)"
        >
          <span class="lib-tab-dot" :style="{ background: lib.color }"></span>
          <span class="lib-tab-name">{{ lib.name }}</span>
          <span class="lib-tab-count">{{ lib.material_count }}</span>
          <span
            v-if="lib.is_owner || auth.isAdmin"
            class="lib-tab-edit"
            title="编辑素材库"
            @click.stop="openLibraryEdit(lib)"
          ><el-icon :size="11"><Edit /></el-icon></span>
        </button>
        <el-tooltip content="新建素材库" placement="top">
          <button class="lib-add" type="button" @click="openLibraryCreate">
            <el-icon :size="16"><Plus /></el-icon>
          </button>
        </el-tooltip>
      </div>
    </el-card>

    <el-card
      shadow="never"
      class="adm-card"
      :class="{ 'is-loading': loading }"
      @dragenter.prevent="onAreaDragEnter"
      @dragover.prevent="onAreaDragOver"
      @dragleave.prevent="onAreaDragLeave"
      @drop.prevent="onAreaDrop"
    >
      <GridSkeleton v-if="loading" variant="assets" :rows="6" :cols="4" thumb />
      <TransitionGroup name="asset-card" tag="div" class="mat-grid">
        <!-- 上传卡片：与已上传卡片等尺寸，固定排在第一位 -->
        <div
          key="__upload_card__"
          class="adm-card adm-card--hover mat-item upload-card"
          :class="{ 'is-dragover': draggingFile }"
          role="button"
          tabindex="0"
          :title="activeKey ? `点击选择图片，上传到「${libName(activeKey)}」` : '请先新建素材库'"
          @click="openFilePicker"
          @keydown.enter="openFilePicker"
        >
          <div class="upload-cover">
            <div class="upload-orbit"><el-icon :size="34"><UploadFilled /></el-icon></div>
            <div class="upload-cover-title">拖入图片上传</div>
            <div class="upload-cover-sub">或点击选择图片</div>
            <span class="upload-format">PNG / JPG</span>
          </div>
          <div class="upload-card-body">
            <span class="upload-card-title">添加图片</span>
            <span class="upload-card-sub">上传到「{{ libName(activeKey) }}」</span>
          </div>
        </div>

        <!-- 上传中的卡片：显示进度与成功动画 -->
        <div v-for="u in uploading" :key="u.id" class="adm-card adm-card--hover mat-item is-uploading">
          <div class="mat-cover">
            <img v-if="u.preview" :src="u.preview" class="mat-cover-img" alt="上传预览" />
            <div v-else class="mat-cover-empty"><el-icon :size="24"><Picture /></el-icon></div>
            <Transition name="result-pop">
              <div v-if="u.status" class="upload-result" :class="`is-${u.status}`">
                <el-icon :size="34"><CircleCheckFilled v-if="u.status === 'success'" /><WarningFilled v-else /></el-icon>
                <span>{{ u.status === 'success' ? '上传成功' : '上传失败' }}</span>
              </div>
            </Transition>
          </div>
          <div class="mat-body">
            <div class="upload-name">{{ u.name }}</div>
            <div class="upload-progress">
              <el-progress :percentage="u.percent" :stroke-width="6" :show-text="false" :status="u.status === 'error' ? 'exception' : undefined" />
              <span>{{ u.status === 'success' ? '完成' : u.status === 'error' ? '失败' : `${u.percent}%` }}</span>
            </div>
          </div>
        </div>

        <el-card
          v-for="m in materials"
          :key="m.id"
          shadow="never"
          class="adm-card adm-card--hover mat-item"
          :class="{ 'is-editing': editingId === m.id }"
          :body-style="{ padding: '0' }"
          :draggable="(m.is_owner || auth.isAdmin) && editingId !== m.id"
          @dragstart="onMatDragStart($event, m)"
          @dragend="onMatDragEnd"
        >
          <div class="mat-cover">
            <el-image
              v-if="m.images && m.images.length"
              :src="m.images[0].file_path"
              :preview-src-list="m.images.map((i) => i.file_path)"
              preview-teleported
              fit="cover"
              class="mat-cover-img"
            />
            <div v-else class="mat-cover-empty">
              <el-icon :size="24"><Picture /></el-icon>
              <span>暂无图片</span>
            </div>
            <div class="mat-badges">
              <span class="badge-chip is-owner">{{ m.owner_name || '系统' }}</span>
            </div>
            <div v-if="m.is_owner || auth.isAdmin" class="cover-remove">
              <button type="button" class="cover-icon-btn is-move" title="移动到其它素材库" @click.stop="openMove(m)">
                <el-icon :size="15"><Sort /></el-icon>
              </button>
              <button type="button" class="cover-icon-btn" title="删除素材" @click.stop="remove(m)">
                <el-icon :size="15"><Delete /></el-icon>
              </button>
            </div>
          </div>
          <div class="mat-body">
            <div class="mat-title-row">
              <template v-if="editingId === m.id">
                <el-input
                  v-model="editingForm.name"
                  size="small"
                  class="inline-input"
                  maxlength="60"
                  placeholder="名称"
                  @click.stop
                />
              </template>
              <template v-else>
                <el-tooltip :content="m.name" placement="top" :disabled="!m.name">
                  <span class="mat-name">{{ m.name }}</span>
                </el-tooltip>
                <button
                  v-if="m.is_owner || auth.isAdmin"
                  type="button"
                  class="name-edit"
                  title="编辑名称与备注"
                  @click.stop="startEdit(m)"
                ><el-icon :size="13"><Edit /></el-icon></button>
              </template>
            </div>
            <el-input
              v-if="editingId === m.id"
              v-model="editingForm.description"
              type="textarea"
              :rows="2"
              resize="none"
              class="inline-input desc-input"
              maxlength="200"
              placeholder="备注"
              @click.stop
            />
            <el-tooltip v-else :content="m.description || '暂无备注'" placement="bottom" :disabled="!m.description">
              <div class="mat-desc">
                {{ m.description || '暂无备注' }}
              </div>
            </el-tooltip>
          </div>
        </el-card>
      </TransitionGroup>
    </el-card>

    <Transition name="drop-fade">
      <div v-if="draggingFile" class="drop-overlay">
        <div class="drop-panel">
          <div class="drop-icon"><el-icon :size="40"><UploadFilled /></el-icon></div>
          <div class="drop-title">松开鼠标上传到「{{ libName(dropLib || activeKey) }}」</div>
          <div class="drop-sub">仅支持 png / jpg，图片文件名作为素材名称</div>
        </div>
      </div>
    </Transition>

    <input
      ref="fileInput"
      type="file"
      accept="image/png,image/jpeg"
      multiple
      class="hidden-file"
      @change="onPicked"
    />

    <!-- 素材库编辑弹窗 -->
    <el-dialog v-model="libDialog.visible" width="420px" :close-on-click-modal="false">
      <template #header>
        <DialogHeader
          :icon="FolderOpened"
          :title="libDialog.isEdit ? '编辑素材库' : '新建素材库'"
          sub="素材库用于归类共享素材，可自定义名称与颜色"
          tone="amber"
        />
      </template>
      <el-form label-width="88px" label-position="right">
        <el-form-item label="素材库名称" required>
          <el-input v-model="libDialog.form.name" placeholder="如：人物库、服装库、场景库" maxlength="30" />
        </el-form-item>
        <el-form-item label="标签颜色">
          <div class="lib-color-row">
            <el-color-picker v-model="libDialog.form.color" />
            <span class="lib-color-tip">{{ libDialog.form.color }}</span>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button
          v-if="libDialog.isEdit && (libDialog.row?.is_owner || auth.isAdmin)"
          type="danger" plain @click="removeLibrary(libDialog.row)"
        >删除素材库</el-button>
        <el-button @click="libDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="libDialog.saving" @click="saveLibrary">保存</el-button>
      </template>
    </el-dialog>

    <!-- 移动到其它素材库 -->
    <el-dialog v-model="moveDialog.visible" width="400px" :close-on-click-modal="false">
      <template #header>
        <DialogHeader
          :icon="Sort"
          title="移动素材"
          :sub="`「${moveDialog.name}」将移动到所选素材库`"
          tone="amber"
        />
      </template>
      <div class="move-list">
        <button
          v-for="lib in libraries"
          :key="lib.id"
          type="button"
          class="move-lib"
          :class="{ 'is-current': String(lib.id) === String(moveDialog.fromLib) }"
          :disabled="String(lib.id) === String(moveDialog.fromLib)"
          @click="doMove(lib)"
        >
          <span class="lib-tab-dot" :style="{ background: lib.color }"></span>
          <span>{{ lib.name }}</span>
          <span v-if="String(lib.id) === String(moveDialog.fromLib)" class="move-current">当前库</span>
        </button>
      </div>
      <template #footer>
        <el-button @click="moveDialog.visible = false">取消</el-button>
      </template>
    </el-dialog>

    <ConfirmDialog
      v-model="confirm.visible"
      :title="confirm.title"
      :message="confirm.message"
      :loading="confirm.loading"
      @confirm="doRemove"
    />

    <DuplicateImageDialog
      v-model="dupDialog.visible"
      :original-name="dupDialog.originalName"
      :copy-name="dupDialog.copyName"
      @choose="onDupChoose"
      @cancel="onDupCancel"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Delete, Edit, FolderOpened, Picture, Plus, Search, Sort, UploadFilled, WarningFilled } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import DuplicateImageDialog from '../components/ui/DuplicateImageDialog.vue'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const ALLOWED = /\.(png|jpe?g)$/i

const loading = ref(false)
const libraries = ref([])
const materials = ref([])
const allMaterials = ref([])
const activeKey = ref('')
const keyword = ref('')
const scope = ref('all')

const draggingFile = ref(false)
const dropLib = ref('')
const uploading = ref([])
const fileInput = ref(null)
const movingMaterial = ref(null)

const editingId = ref(null)
const editingForm = reactive({ name: '', description: '' })

const libDialog = reactive({
  visible: false, isEdit: false, row: null, saving: false,
  form: { name: '', color: '#4a7cc4' }
})
const confirm = reactive({ visible: false, loading: false, title: '', message: '', kind: '', id: null })

// 重复图片处理弹窗：按目标素材库内的名称判重，resolve 回传用户选择
const dupDialog = reactive({ visible: false, originalName: '', copyName: '', resolve: null })
let dupResolve = null

function askDuplicate(originalName, libraryMaterials) {
  dupDialog.originalName = originalName
  dupDialog.copyName = nextCopyName(originalName, libraryMaterials)
  dupDialog.visible = true
  return new Promise((resolve) => { dupResolve = resolve })
}

function onDupChoose(choice) {
  if (dupResolve) dupResolve(choice)
  dupResolve = null
}

function onDupCancel() {
  if (dupResolve) dupResolve(null)
  dupResolve = null
}

function nextCopyName(name, libraryMaterials) {
  const existing = new Set((libraryMaterials || []).map((m) => m.name))
  let candidate = `${name}(副本)`
  let n = 2
  while (existing.has(candidate)) candidate = `${name}(副本${n++})`
  return candidate
}
const moveDialog = reactive({ visible: false, id: null, name: '', fromLib: null })

const activeLib = computed(() => libraries.value.find((l) => String(l.id) === activeKey.value))

function libTabStyle(lib) {
  if (activeKey.value !== String(lib.id)) return {}
  return { '--lib-active': lib.color || '#4a7cc4' }
}

function libName(id) {
  const lib = libraries.value.find((l) => String(l.id) === String(id))
  return lib ? lib.name : '未归类'
}

async function loadLibraries(keepActive = true) {
  try {
    const { data } = await api.get('/material-libraries', { params: { scope: scope.value } })
    libraries.value = Array.isArray(data) ? data : []
    if (!keepActive || !libraries.value.some((l) => String(l.id) === activeKey.value)) {
      activeKey.value = libraries.value.length ? String(libraries.value[0].id) : ''
    }
  } catch (e) {
    libraries.value = []
    activeKey.value = ''
  }
}

async function loadMaterials() {
  loading.value = true
  try {
    const requests = libraries.value.map((l) =>
      api.get(`/material-libraries/${l.id}/materials`, {
        params: { scope: scope.value, keyword: keyword.value }
      }).then((r) => Array.isArray(r.data) ? r.data : [])
    )
    const lists = await Promise.all(requests)
    allMaterials.value = lists.flat()
    materials.value = activeKey.value
      ? allMaterials.value.filter((m) => String(m.library_id) === activeKey.value)
      : []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载素材失败')
    materials.value = []
    allMaterials.value = []
  } finally {
    loading.value = false
  }
}

async function reloadAll() {
  await loadLibraries()
  await loadMaterials()
}

function selectLibrary(lib) {
  activeKey.value = String(lib.id)
  materials.value = activeKey.value
    ? allMaterials.value.filter((m) => String(m.library_id) === activeKey.value)
    : []
}

function openLibraryCreate() {
  libDialog.isEdit = false
  libDialog.row = null
  libDialog.form = { name: '', color: '#4a7cc4' }
  libDialog.visible = true
}

function openLibraryEdit(lib) {
  libDialog.isEdit = true
  libDialog.row = lib
  libDialog.form = { name: lib.name, color: lib.color || '#4a7cc4' }
  libDialog.visible = true
}

async function saveLibrary() {
  const name = (libDialog.form.name || '').trim()
  if (!name) return ElMessage.warning('请输入素材库名称')
  libDialog.saving = true
  try {
    if (libDialog.isEdit) {
      const { data } = await api.put(`/material-libraries/${libDialog.row.id}`, {
        name, color: libDialog.form.color
      })
      activeKey.value = String(data.id)
    } else {
      const { data } = await api.post('/material-libraries', {
        name, color: libDialog.form.color
      })
      activeKey.value = String(data.id)
    }
    libDialog.visible = false
    ElMessage.success('素材库已保存')
    await reloadAll()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    libDialog.saving = false
  }
}

function removeLibrary(lib) {
  libDialog.visible = false
  confirm.title = '删除素材库'
  confirm.message = `确定删除素材库「${lib.name}」吗？库内需无素材。`
  confirm.kind = 'library'
  confirm.id = lib.id
  confirm.visible = true
}

function startEdit(m) {
  if (!(m.is_owner || auth.isAdmin)) return
  editingId.value = m.id
  editingForm.name = m.name || ''
  editingForm.description = m.description || ''
}

async function saveEdit() {
  const id = editingId.value
  if (!id) return
  const m = materials.value.find((x) => x.id === id)
  if (!m) return
  const name = (editingForm.name || '').trim()
  const description = editingForm.description || ''
  editingId.value = null
  if (!name) {
    ElMessage.warning('素材名称不能为空')
    return
  }
  if (m.name === name && (m.description || '') === description) return
  try {
    const { data } = await api.patch(`/material-libraries/materials/${id}`, { name, description })
    Object.assign(m, data)
    ElMessage.success('修改成功')
  } catch (e) {
    // 素材可能已在其它标签页被删除：刷新列表，避免继续操作已失效的卡片
    if (e.response?.status === 404) {
      await reloadAll()
      ElMessage.warning('该素材已不存在，列表已刷新')
    } else {
      ElMessage.error(e.response?.data?.detail || '修改失败')
    }
  }
}

function onDocClick(event) {
  if (!editingId.value) return
  const editingCard = document.querySelector('.mat-item.is-editing')
  if (editingCard && editingCard.contains(event.target)) return
  saveEdit()
}

function remove(m) {
  confirm.title = '删除素材'
  confirm.message = `确定删除素材「${m.name}」吗？删除后无法恢复。`
  confirm.kind = 'material'
  confirm.id = m.id
  confirm.visible = true
}

async function doRemove() {
  confirm.loading = true
  try {
    const path = confirm.kind === 'library'
      ? `/material-libraries/${confirm.id}`
      : `/material-libraries/materials/${confirm.id}`
    await api.delete(path)
    ElMessage.success('已删除')
    confirm.visible = false
    if (confirm.kind === 'library') activeKey.value = ''
    await reloadAll()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    confirm.loading = false
  }
}

function hasFiles(event) {
  return Array.from(event?.dataTransfer?.types || []).includes('Files')
}

function onLibDragEnter(event, lib) {
  if (!hasFiles(event)) return
  draggingFile.value = true
  dropLib.value = String(lib.id)
}

function onLibDragOver(event, lib) {
  if (!hasFiles(event)) return
  draggingFile.value = true
  dropLib.value = String(lib.id)
}

function onLibDragLeave(lib) {
  if (dropLib.value === String(lib.id)) dropLib.value = ''
  if (!dropLib.value) draggingFile.value = false
}

function onAreaDragEnter(event) {
  if (!hasFiles(event)) return
  draggingFile.value = true
  dropLib.value = ''
}
function onAreaDragOver(event) {
  if (!hasFiles(event)) return
  draggingFile.value = true
  dropLib.value = ''
}
function onAreaDragLeave() {
  if (!dropLib.value) draggingFile.value = false
}
function onAreaDrop(event) {
  if (!hasFiles(event)) return
  draggingFile.value = false
  dropLib.value = ''
  uploadFiles(Array.from(event?.dataTransfer?.files || []), activeKey.value)
}

async function onLibDrop(event, lib) {
  draggingFile.value = false
  dropLib.value = ''
  const files = Array.from(event?.dataTransfer?.files || [])
  if (files.length) {
    await uploadFiles(files, String(lib.id))
    return
  }
  const materialId = event?.dataTransfer?.getData('text/material-id') || event?.dataTransfer?.getData('text/plain')
  if (materialId) {
    moveDialog.fromLib = null
    await moveMaterial(Number(materialId), lib)
  }
}

function onMatDragStart(event, m) {
  movingMaterial.value = m
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/plain', String(m.id))
  event.dataTransfer.setData('text/material-id', String(m.id))
}

function onMatDragEnd() {
  movingMaterial.value = null
}

function openMove(m) {
  moveDialog.id = m.id
  moveDialog.name = m.name
  moveDialog.fromLib = m.library_id
  moveDialog.visible = true
}

async function doMove(lib) {
  const target = { id: lib.id, name: lib.name }
  moveDialog.visible = false
  await moveMaterial(moveDialog.id, target)
}

async function moveMaterial(materialId, lib) {
  if (!materialId || String(lib.id) === String(moveDialog.fromLib ?? activeKey.value)) return
  try {
    await api.patch(`/material-libraries/materials/${materialId}`, { library_id: lib.id })
    ElMessage.success(`已移动到「${lib.name}」`)
    activeKey.value = String(lib.id)
    moveDialog.fromLib = null
    await reloadAll()
  } catch (e) {
    if (e.response?.status === 404) {
      await reloadAll()
      ElMessage.warning('素材或目标素材库已不存在，列表已刷新')
    } else {
      ElMessage.error(e.response?.data?.detail || '移动失败')
    }
  }
}

function openFilePicker() {
  // 若正在卡片内编辑，先完成保存，避免编辑状态干扰上传
  if (editingId.value) saveEdit()
  fileInput.value?.click()
}

function onPicked(event) {
  uploadFiles(Array.from(event?.target?.files || []), activeKey.value)
  event.target.value = ''
}

function baseName(filename) {
  return (filename || '未命名图片').replace(ALLOWED, '')
}

async function uploadFiles(files, libraryId) {
  if (!files.length) return
  let targetLib = String(libraryId || activeKey.value)
  // 页面可能停留在已删除的素材库上（例如其它标签页刚删过），上传前先校正目标库
  if (targetLib && !libraries.value.some((l) => String(l.id) === targetLib)) {
    await loadLibraries(false)
    if (targetLib && !libraries.value.some((l) => String(l.id) === targetLib)) {
      targetLib = activeKey.value
      ElMessage.warning(`原素材库已不存在，已切换到「${libName(targetLib)}」`)
    }
  }
  if (!targetLib) return ElMessage.warning('请先新建一个素材库')
  const valid = files.filter((f) => ALLOWED.test(f?.name || ''))
  if (valid.length !== files.length) ElMessage.warning('已忽略非 png / jpg 格式图片')
  if (!valid.length) return

  let done = 0
  // 目标库当前素材，用于库内判重
  const libMaterials = allMaterials.value.filter((m) => String(m.library_id) === String(targetLib))
  for (const file of valid) {
    const base = baseName(file.name)
    // 按名称判重（同一素材库内）：命中则让用户选择改名 / 覆盖 / 创建副本
    const dup = libMaterials.find((m) => m.name === base)
    let finalName = base
    let overwriteId = null
    if (dup) {
      const choice = await askDuplicate(base, libMaterials)
      if (!choice) continue // 取消：跳过该文件
      if (choice.action === 'overwrite') {
        overwriteId = dup.id
      } else if (choice.action === 'rename') {
        finalName = choice.name
      } else if (choice.action === 'copy') {
        finalName = dupDialog.copyName
      }
    }

    const task = {
      id: `${Date.now()}-${Math.random()}`,
      name: finalName,
      percent: 0,
      status: '',
      preview: URL.createObjectURL(file)
    }
    uploading.value.push(task)
    try {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post('/upload', form, {
        onUploadProgress: (e) => {
          if (e.total) task.percent = Math.min(96, Math.round((e.loaded / e.total) * 100))
        }
      })
      task.percent = 99
      const payload = {
        name: finalName,
        description: '',
        tags: [],
        images: [{ file_path: data.url, sort: 0 }]
      }
      if (overwriteId) {
        // 覆盖：保留原素材的描述与标签，只替换图片，名称不变
        const origin = libMaterials.find((m) => m.id === overwriteId)
        payload.name = base
        payload.description = origin?.description || ''
        payload.tags = origin?.tags || []
        await api.put(`/material-libraries/materials/${overwriteId}`, payload)
      } else {
        await api.post(`/material-libraries/${targetLib}/materials`, payload)
      }
      task.percent = 100
      task.status = 'success'
      done += 1
      ElMessage.success(`${task.name} ${overwriteId ? '已覆盖' : '上传成功'}`)
      activeKey.value = String(targetLib)
      await reloadAll()
      // 同步本地判重集合：新建的素材加入，覆盖的保持原名
      if (!overwriteId) libMaterials.push({ id: -1, name: finalName, library_id: Number(targetLib) })
      await new Promise((resolve) => setTimeout(resolve, 900))
    } catch (e) {
      task.status = 'error'
      if (e.response?.status === 404) {
        await reloadAll()
        ElMessage.error(`${task.name} 上传失败：目标素材库已不存在，列表已刷新`)
      } else {
        ElMessage.error(`${task.name} 上传失败：${e.response?.data?.detail || '请重试'}`)
      }
      await new Promise((resolve) => setTimeout(resolve, 900))
    } finally {
      URL.revokeObjectURL(task.preview)
      uploading.value = uploading.value.filter((u) => u.id !== task.id)
    }
  }
}

function onVisibilityChange() {
  // 切回页面时自动同步服务端数据，避免继续操作其它标签页已删除的素材/素材库
  if (document.visibilityState === 'visible' && !editingId.value && !uploading.value.length) {
    reloadAll()
  }
}

onMounted(async () => {
  await loadLibraries(false)
  await loadMaterials()
  document.addEventListener('click', onDocClick)
  document.addEventListener('visibilitychange', onVisibilityChange)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<style scoped>
.lib-bar-card :deep(.el-card__body) { padding: 10px 14px; }
.lib-head {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}
.lib-head-title { font-size: 13px; font-weight: 700; color: var(--adm-text-primary); }
.lib-head-tip { font-size: 12px; color: var(--adm-text-secondary); flex: 1; }
.lib-add {
  width: 28px;
  height: 28px;
  flex-shrink: 0;
  border: none;
  border-radius: 50%;
  background: var(--el-color-primary);
  color: #fff;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.15s ease, box-shadow 0.15s ease;
}
.lib-add:hover { transform: scale(1.06); box-shadow: 0 4px 12px rgba(64, 158, 255, 0.28); }
.lib-tab-list { display: flex; flex-wrap: wrap; gap: 8px; min-width: 0; }
.lib-tab {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 11px;
  border: 1px solid var(--adm-border);
  border-radius: 16px;
  background: var(--adm-panel-soft);
  color: var(--adm-text-secondary);
  font-size: 12.5px;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.lib-tab:hover { background: var(--adm-panel-hover); }
.lib-tab.is-active {
  background: var(--lib-active, var(--adm-blue-bg));
  color: #fff;
  border-color: transparent;
  font-weight: 600;
}
.lib-tab.is-dropover {
  border-color: var(--el-color-primary);
  box-shadow: 0 0 0 3px var(--adm-active-bg);
}
.lib-tab-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
.lib-tab.is-active .lib-tab-dot { background: #fff !important; }
.lib-tab-name { white-space: nowrap; }
.lib-tab-count { font-size: 11px; opacity: 0.75; font-variant-numeric: tabular-nums; }
.lib-tab-edit { display: inline-flex; align-items: center; opacity: 0.6; margin-left: 2px; }
.lib-tab-edit:hover { opacity: 1; }
.lib-color-row { display: flex; align-items: center; gap: 10px; }
.lib-color-tip { font-size: 12px; color: var(--adm-text-placeholder); font-variant-numeric: tabular-nums; }

.mat-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--asset-grid-min, 230px), 1fr));
  gap: var(--asset-grid-gap, 18px);
}
.asset-card-move,
.asset-card-enter-active,
.asset-card-leave-active { transition: transform 0.32s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.32s ease; }
.asset-card-enter-from { opacity: 0; transform: translateY(14px) scale(0.96); }
.asset-card-leave-to { opacity: 0; transform: scale(0.95); }
.mat-item { overflow: hidden; }
.mat-item.is-uploading { border: 1px dashed var(--el-color-primary); }
.is-uploading .mat-body { height: 89px; box-sizing: border-box; }

/* 第一张卡片：拖拽上传入口，尺寸与已上传卡片一致 */
.upload-card {
  cursor: pointer;
  border: 1px dashed var(--adm-border-deep);
  background: var(--adm-panel-soft);
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.2s ease;
}
.upload-card:hover,
.upload-card:focus-visible {
  transform: translateY(-3px);
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
  box-shadow: 0 10px 26px rgba(37, 99, 235, 0.14);
  outline: none;
}
.upload-card.is-dragover { border-color: var(--el-color-primary); animation: upload-card-pulse 1s ease-in-out infinite; }
.upload-cover {
  height: var(--asset-cover-h, 200px);
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(145deg, var(--adm-panel-soft), var(--adm-surface));
}
.upload-orbit {
  width: 66px;
  height: 66px;
  display: grid;
  place-items: center;
  border-radius: 50%;
  color: #fff;
  background: linear-gradient(135deg, #5b8def, #3f6fd8);
  box-shadow: 0 10px 24px rgba(63, 111, 216, 0.3);
  animation: upload-float 2.4s ease-in-out infinite;
}
.upload-card:hover .upload-orbit { animation-duration: 1.1s; }
.upload-cover-title { margin-top: 12px; font-size: 15px; font-weight: 700; color: var(--adm-text-primary); }
.upload-cover-sub { margin-top: 4px; font-size: 12px; color: var(--adm-text-secondary); }
.upload-format {
  position: absolute;
  top: 12px;
  right: 12px;
  padding: 2px 7px;
  border-radius: 8px;
  background: var(--adm-surface);
  border: 1px solid var(--adm-border);
  font-size: 10px;
  color: var(--adm-text-placeholder);
}
.upload-card-body { height: 89px; box-sizing: border-box; padding: 14px; }
.upload-card-title { display: block; font-size: 15px; line-height: 21px; font-weight: 700; color: var(--adm-text-primary); }
.upload-card-sub { display: block; margin-top: 4px; font-size: 13px; line-height: 18px; color: var(--adm-text-secondary); }
@keyframes upload-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-6px); }
}
@keyframes upload-card-pulse {
  0%, 100% { box-shadow: 0 0 0 0 rgba(59, 130, 246, 0.28); }
  50% { box-shadow: 0 0 0 8px rgba(59, 130, 246, 0); }
}
.upload-result {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  background: rgba(255, 255, 255, 0.92);
  color: #2e9e6b;
  font-size: 14px;
  font-weight: 700;
}
.upload-result.is-error { color: var(--el-color-danger); }
.result-pop-enter-active { animation: result-pop-in 0.36s cubic-bezier(0.2, 1.3, 0.4, 1) both; }
.result-pop-leave-active { animation: result-pop-out 0.2s ease both; }
@keyframes result-pop-in {
  from { opacity: 0; transform: scale(0.85); }
  to { opacity: 1; transform: scale(1); }
}
@keyframes result-pop-out {
  from { opacity: 1; }
  to { opacity: 0; }
}
.mat-cover { position: relative; background: var(--adm-panel-soft); }
.mat-cover-img { width: 100%; height: var(--asset-cover-h, 200px); display: block; object-fit: cover; }
.mat-badges {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  box-sizing: border-box;
  padding: 6px 10px;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(2px);
}
.badge-chip {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 6px;
  border: 1px solid rgba(255, 255, 255, 0.5);
  border-radius: 9px;
  background: transparent;
  font-size: 11px;
  font-weight: 500;
  line-height: 1;
}
.badge-chip.is-owner {
  color: #fff;
  background: linear-gradient(135deg, #6a9cf0, #4a7cc4);
  border-color: rgba(255, 255, 255, 0.28);
  box-shadow: 0 2px 6px rgba(37, 99, 235, 0.24);
}
.cover-remove {
  position: absolute;
  top: 10px;
  right: 10px;
  display: flex;
  gap: 6px;
  opacity: 0;
  transition: opacity 0.18s ease;
}
.mat-cover:hover .cover-remove { opacity: 1; }
.cover-icon-btn {
  width: 28px;
  height: 28px;
  display: grid;
  place-items: center;
  padding: 0;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  color: #fff;
  background: var(--el-color-danger);
}
.cover-icon-btn.is-move { background: #7b62c9; }
.cover-icon-btn:hover { filter: brightness(1.08); }
.name-edit {
  flex-shrink: 0;
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  padding: 0;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  color: var(--adm-text-secondary);
  background: transparent;
}
.name-edit:hover { color: var(--el-color-primary); background: var(--adm-active-bg); }
.move-list { display: flex; flex-direction: column; gap: 8px; }
.move-lib {
  display: flex;
  align-items: center;
  gap: 8px;
  height: 38px;
  padding: 0 12px;
  border: 1px solid var(--adm-border);
  border-radius: 9px;
  cursor: pointer;
  background: var(--adm-panel-soft);
  color: var(--adm-text-regular);
  font-size: 13px;
  text-align: left;
}
.move-lib:not(:disabled):hover { border-color: var(--el-color-primary); background: var(--adm-active-bg); }
.move-lib:disabled { cursor: default; opacity: 0.7; }
.move-current { margin-left: auto; font-size: 11px; color: var(--adm-text-placeholder); }
.mat-cover-empty {
  height: var(--asset-cover-h, 200px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--adm-text-placeholder);
  font-size: 12px;
}
.mat-body { padding: 14px; }
.mat-title-row { display: flex; align-items: center; gap: 8px; }
.mat-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--adm-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 0 1 auto;
  min-width: 0;
  max-width: calc(100% - 24px);
}
.mat-desc {
  margin-top: 4px;
  font-size: 13px;
  color: var(--adm-text-secondary);
  line-height: 18px;
  height: 36px;
  overflow: hidden;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  text-overflow: ellipsis;
}
.inline-input { flex: 1 1 auto; min-width: 0; }
.desc-input { margin-top: 4px; }
.mat-item.is-editing { border-color: var(--el-color-primary); }
.upload-name {
  font-size: 15px;
  font-weight: 700;
  color: var(--adm-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.upload-progress {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 8px;
  font-size: 12px;
  color: var(--el-color-primary);
}
.upload-progress :deep(.el-progress) { flex: 1; }

.drop-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: grid;
  place-items: center;
  background: rgba(20, 34, 58, 0.42);
  backdrop-filter: blur(2px);
  pointer-events: none;
}
.drop-panel {
  width: min(460px, 80vw);
  padding: 36px 24px;
  border: 2px dashed #fff;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
  text-align: center;
  animation: drop-pulse 1.2s ease-in-out infinite;
}
.drop-icon { color: var(--el-color-primary); }
.drop-title { margin-top: 12px; font-size: 18px; font-weight: 700; color: var(--adm-text-primary); }
.drop-sub { margin-top: 6px; font-size: 12.5px; color: var(--adm-text-secondary); }
@keyframes drop-pulse {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.02); }
}
.drop-fade-enter-active, .drop-fade-leave-active { transition: opacity 0.16s ease; }
.drop-fade-enter-from, .drop-fade-leave-to { opacity: 0; }
.hidden-file { display: none; }

/* 小屏封面收窄后，上传卡图标与文案同比收缩，避免图标挤占封面 */
@media (max-width: 1366px) {
  .upload-orbit { width: 54px; height: 54px; }
  .upload-cover-title { margin-top: 8px; font-size: 14px; }
  .upload-cover-sub { font-size: 11px; }
  .mat-body { padding: 11px; }
  .upload-card-body { height: 80px; padding: 11px; }
  .is-uploading .mat-body { height: 80px; }
}
</style>
