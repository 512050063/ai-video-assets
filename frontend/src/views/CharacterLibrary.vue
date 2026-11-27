<template>
  <div
    class="stack asset-drop-zone"
    :class="{ 'is-dragover': dragging }"
    @dragenter.prevent="onDragEnter"
    @dragover.prevent="onDragOver"
    @dragleave.prevent="onDragLeave"
    @drop.prevent="onDrop"
  >
    <PageHeader
      :icon="User"
      title="人物资产"
      tone="amber"
      :desc="`共 ${list.length} 个人物，可被多条视频制作复用`"
    >
      <template #extra>
        <el-input v-model="keyword" placeholder="搜索人物名称" clearable style="width: 200px">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="scope" style="width: 120px" @change="load">
          <el-option value="all" label="全部成员" />
          <el-option value="mine" label="仅我的" />
        </el-select>
      </template>
    </PageHeader>

    <el-card shadow="never" class="adm-card" :class="{ 'is-loading': loading }">
      <GridSkeleton v-if="loading" variant="assets" :rows="6" :cols="4" thumb />
      <TransitionGroup name="asset-card" tag="div" class="char-grid">
        <!-- 上传卡片：与已上传卡片等尺寸，固定排在第一位 -->
        <div
          key="__upload_card__"
          class="adm-card adm-card--hover char-item upload-card"
          :class="{ 'is-dragover': dragging }"
          role="button"
          tabindex="0"
          title="点击选择图片，或从文件夹拖入图片"
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
            <span class="upload-card-sub">文件名作为人物名称</span>
          </div>
        </div>

        <!-- 上传中的卡片：显示进度与成功动画 -->
        <div v-for="u in uploading" :key="u.id" class="adm-card adm-card--hover char-item is-uploading">
          <div class="char-cover">
            <img v-if="u.preview" :src="u.preview" class="char-cover-img" alt="上传预览" />
            <div v-else class="char-cover-empty"><el-icon :size="24"><Picture /></el-icon></div>
            <Transition name="result-pop">
              <div v-if="u.status" class="upload-result" :class="`is-${u.status}`">
                <el-icon :size="34"><CircleCheckFilled v-if="u.status === 'success'" /><WarningFilled v-else /></el-icon>
                <span>{{ u.status === 'success' ? '上传成功' : '上传失败' }}</span>
              </div>
            </Transition>
          </div>
          <div class="char-body">
            <div class="upload-name">{{ u.name }}</div>
            <div class="upload-progress">
              <el-progress :percentage="u.percent" :stroke-width="6" :show-text="false" :status="u.status === 'error' ? 'exception' : undefined" />
              <span>{{ u.status === 'success' ? '完成' : u.status === 'error' ? '失败' : `${u.percent}%` }}</span>
            </div>
          </div>
        </div>

        <el-card
          v-for="c in list"
          :key="c.id"
          shadow="never"
          class="adm-card adm-card--hover char-item"
          :class="{ 'is-editing': editingId === c.id }"
          :body-style="{ padding: '0' }"
        >
          <div class="char-cover">
            <el-image
              v-if="c.images && c.images.length"
              :src="c.images[0].file_path"
              :preview-src-list="c.images.map((i) => i.file_path)"
              preview-teleported
              fit="cover"
              class="char-cover-img"
            />
            <div v-else class="char-cover-empty">
              <el-icon :size="24"><User /></el-icon>
              <span>暂无图片</span>
            </div>
            <div class="char-badges">
              <span class="badge-chip is-owner">{{ c.owner_name || '系统' }}</span>
              <span class="badge-plain">用了 {{ c.production_count || 0 }} 次</span>
            </div>
            <div v-if="c.is_owner || auth.isAdmin" class="cover-remove">
              <button type="button" class="cover-icon-btn" title="删除人物" @click="remove(c)">
                <el-icon :size="15"><Delete /></el-icon>
              </button>
            </div>
          </div>

          <div class="char-body">
            <div class="char-title-row">
              <template v-if="editingId === c.id">
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
                <el-tooltip :content="c.name" placement="top" :disabled="!c.name">
                  <span class="char-name">{{ c.name }}</span>
                </el-tooltip>
                <button
                  v-if="c.is_owner || auth.isAdmin"
                  type="button"
                  class="name-edit"
                  title="编辑名称与备注"
                  @click.stop="startEdit(c)"
                ><el-icon :size="13"><Edit /></el-icon></button>
              </template>
            </div>
            <el-input
              v-if="editingId === c.id"
              v-model="editingForm.description"
              type="textarea"
              :rows="2"
              resize="none"
              class="inline-input desc-input"
              maxlength="200"
              placeholder="备注"
              @click.stop
            />
            <el-tooltip v-else :content="c.description || '暂无备注'" placement="bottom" :disabled="!c.description">
              <div class="char-desc">
                {{ c.description || '暂无备注' }}
              </div>
            </el-tooltip>
          </div>
        </el-card>
      </TransitionGroup>
    </el-card>

    <!-- 拖拽遮罩：显示上传动画 -->
    <Transition name="drop-fade">
      <div v-if="dragging" class="drop-overlay">
        <div class="drop-panel">
          <div class="drop-icon"><el-icon :size="40"><UploadFilled /></el-icon></div>
          <div class="drop-title">松开鼠标上传图片</div>
          <div class="drop-sub">仅支持 png / jpg，图片文件名作为人物名称</div>
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

    <ConfirmDialog
      v-model="confirm.visible"
      title="删除人物"
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
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Delete, Edit, Picture, Search, UploadFilled, User, WarningFilled } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import DuplicateImageDialog from '../components/ui/DuplicateImageDialog.vue'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const ALLOWED = /\.(png|jpe?g)$/i

const loading = ref(false)
const list = ref([])
const keyword = ref('')
const scope = ref('all')

const dragging = ref(false)
const dragDepth = ref(0)
const uploading = ref([])
const fileInput = ref(null)

const editingId = ref(null)
const editingForm = reactive({ name: '', description: '' })

const confirm = reactive({ visible: false, loading: false, message: '', id: null })
// 重复图片处理弹窗：resolve 用于把用户选择回传给 async 上传流程
const dupDialog = reactive({ visible: false, originalName: '', copyName: '', resolve: null })
let dupResolve = null

function askDuplicate(originalName) {
  dupDialog.originalName = originalName
  dupDialog.copyName = nextCopyName(originalName)
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

// 生成不冲突的副本名：原名(副本)、原名(副本2)...
function nextCopyName(name) {
  const existing = new Set(list.value.map((c) => c.name))
  let candidate = `${name}(副本)`
  let n = 2
  while (existing.has(candidate)) candidate = `${name}(副本${n++})`
  return candidate
}

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/characters', {
      params: { scope: scope.value, keyword: keyword.value, asset_type: 'character' }
    })
    list.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败，请重试')
  } finally {
    loading.value = false
  }
}

function startEdit(c) {
  if (!(c.is_owner || auth.isAdmin)) return
  editingId.value = c.id
  editingForm.name = c.name || ''
  editingForm.description = c.description || ''
}

async function saveEdit() {
  const id = editingId.value
  if (!id) return
  const c = list.value.find((x) => x.id === id)
  if (!c) return
  const name = (editingForm.name || '').trim()
  const description = editingForm.description || ''
  editingId.value = null
  if (!name) {
    ElMessage.warning('名称不能为空')
    return
  }
  if (c.name === name && (c.description || '') === description) return
  try {
    const { data } = await api.patch(`/characters/${id}`, { name, description })
    Object.assign(c, data)
    ElMessage.success('修改成功')
  } catch (e) {
    if (e.response?.status === 404) {
      await load()
      ElMessage.warning('该人物已不存在，列表已刷新')
    } else {
      ElMessage.error(e.response?.data?.detail || '修改失败')
    }
  }
}

function onDocClick(event) {
  if (!editingId.value) return
  const editingCard = document.querySelector('.char-item.is-editing')
  if (editingCard && editingCard.contains(event.target)) return
  saveEdit()
}

function remove(c) {
  confirm.message = `确定删除人物「${c.name}」吗？删除后无法恢复。`
  confirm.id = c.id
  confirm.visible = true
}

async function doRemove() {
  confirm.loading = true
  try {
    await api.delete(`/characters/${confirm.id}`)
    ElMessage.success('已删除')
    confirm.visible = false
    load()
  } catch (e) {
    if (e.response?.status === 404) {
      confirm.visible = false
      await load()
      ElMessage.warning('该人物已不存在，列表已刷新')
    } else {
      ElMessage.error(e.response?.data?.detail || '删除失败')
    }
  } finally {
    confirm.loading = false
  }
}

function onDragEnter() {
  dragDepth.value += 1
  dragging.value = true
}

function onDragOver() {
  dragging.value = true
}

function onDragLeave() {
  dragDepth.value = Math.max(0, dragDepth.value - 1)
  if (dragDepth.value === 0) dragging.value = false
}

function onDrop(event) {
  dragDepth.value = 0
  dragging.value = false
  uploadFiles(Array.from(event?.dataTransfer?.files || []))
}

function openFilePicker() {
  // 卡片内正在编辑时先保存，避免编辑请求干扰上传
  if (editingId.value) saveEdit()
  fileInput.value?.click()
}

function onPicked(event) {
  uploadFiles(Array.from(event?.target?.files || []))
  event.target.value = ''
}

function baseName(filename) {
  return (filename || '未命名图片').replace(ALLOWED, '')
}

async function uploadFiles(files) {
  if (!files.length) return
  const valid = files.filter((f) => ALLOWED.test(f?.name || ''))
  if (valid.length !== files.length) ElMessage.warning('已忽略非 png / jpg 格式图片')
  if (!valid.length) return

  let done = 0
  for (const file of valid) {
    const base = baseName(file.name)
    // 按名称判重：命中同名资产时弹窗让用户选择改名 / 覆盖 / 创建副本
    const dup = list.value.find((c) => c.name === base)
    let finalName = base
    let overwriteId = null
    if (dup) {
      const choice = await askDuplicate(base)
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
        asset_type: 'character',
        description: '',
        tags: [],
        images: [{ file_path: data.url, sort: 0 }]
      }
      if (overwriteId) {
        // 覆盖：借用原资产的描述/标签，只替换图片与名称保持同名
        const origin = list.value.find((c) => c.id === overwriteId)
        payload.description = origin?.description || ''
        payload.tags = origin?.tags || []
        await api.put(`/characters/${overwriteId}`, payload)
      } else {
        await api.post('/characters', payload)
      }
      task.percent = 100
      task.status = 'success'
      done += 1
      ElMessage.success(`${task.name} ${overwriteId ? '已覆盖' : '上传成功'}`)
      await load()
      await new Promise((resolve) => setTimeout(resolve, 900))
    } catch (e) {
      task.status = 'error'
      if (e.response?.status === 404) {
        await load()
        ElMessage.error(`${task.name} 上传失败：数据已变化，列表已刷新，请重试`)
      } else {
        ElMessage.error(`${task.name} 上传失败：${e.response?.data?.detail || '请重试'}`)
      }
      await new Promise((resolve) => setTimeout(resolve, 900))
    } finally {
      URL.revokeObjectURL(task.preview)
      uploading.value = uploading.value.filter((u) => u.id !== task.id)
    }
  }
  if (done) await load()
}

function onVisibilityChange() {
  // 切回页面时同步服务端数据，避免继续操作其它标签页已删除的人物
  if (document.visibilityState === 'visible' && !editingId.value && !uploading.value.length) {
    load()
  }
}

onMounted(() => {
  load()
  document.addEventListener('click', onDocClick)
  document.addEventListener('visibilitychange', onVisibilityChange)
})
onUnmounted(() => {
  document.removeEventListener('click', onDocClick)
  document.removeEventListener('visibilitychange', onVisibilityChange)
})
</script>

<style scoped>
.asset-drop-zone {
  min-height: calc(100vh - 120px);
}
.char-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(var(--asset-grid-min, 230px), 1fr));
  gap: var(--asset-grid-gap, 18px);
}
.asset-card-move,
.asset-card-enter-active,
.asset-card-leave-active { transition: transform 0.32s cubic-bezier(0.2, 0.8, 0.2, 1), opacity 0.32s ease; }
.asset-card-enter-from { opacity: 0; transform: translateY(14px) scale(0.96); }
.asset-card-leave-to { opacity: 0; transform: scale(0.95); }
.char-item { overflow: hidden; }
.char-item.is-uploading { border: 1px dashed var(--el-color-primary); }
.is-uploading .char-body { height: 89px; box-sizing: border-box; }

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
.char-cover { position: relative; background: var(--adm-panel-soft); }
.char-cover-img { width: 100%; height: var(--asset-cover-h, 200px); display: block; object-fit: cover; }
.char-badges {
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
.badge-plain { color: #f1f5f9; font-size: 11px; line-height: 18px; font-weight: 600; text-shadow: 0 1px 2px rgba(0, 0, 0, 0.4); }
.cover-remove {
  position: absolute;
  top: 10px;
  right: 10px;
  opacity: 0;
  transition: opacity 0.18s ease;
}
.char-cover:hover .cover-remove { opacity: 1; }
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
.char-cover-empty {
  height: var(--asset-cover-h, 200px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--adm-text-placeholder);
  font-size: 12px;
}
.char-body { padding: 14px; }
.char-title-row { display: flex; align-items: center; gap: 8px; }
.char-name {
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
.char-desc {
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
.char-item.is-editing { border-color: var(--el-color-primary); }
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
  .char-body { padding: 11px; }
  .upload-card-body { height: 80px; padding: 11px; }
  .is-uploading .char-body { height: 80px; }
}
</style>
