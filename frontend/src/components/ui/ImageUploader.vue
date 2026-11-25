<template>
  <div class="adm-uploader" :class="[`is-${mode}`, `is-${shape}`]">
    <!-- 单图模式：头像 / 主图 -->
    <template v-if="mode === 'single'">
      <el-upload
        class="adm-uploader-single"
        action="/api/upload"
        :headers="uploadHeaders"
        accept=".png,.jpg,.jpeg"
        :show-file-list="false"
        :before-upload="beforeUpload"
        :on-success="onUploadSuccess"
        :on-error="onUploadError"
      >
        <div
          class="adm-uploader-box"
          :class="{ 'is-dragover': dragging }"
          :style="{ width: boxSize, height: boxSize }"
          @dragover.prevent="dragging = true"
          @dragleave.prevent="dragging = false"
          @drop.prevent="onDrop"
        >
          <img v-if="src" :src="src" alt="图片预览" />
          <div v-else class="adm-uploader-fallback">
            <el-icon><component :is="resolvedFallback" /></el-icon>
          </div>
          <div class="adm-uploader-mask">
            <el-icon :size="16"><Camera /></el-icon>
            <span>更换</span>
          </div>
        </div>
      </el-upload>
      <p v-if="tip" class="adm-uploader-tip">{{ tip }}（可拖拽，仅 png / jpg）</p>
    </template>

    <!-- 多图模式：资产图片网格，支持拖拽上传 + 点击放大预览 -->
    <template v-else>
      <div
        class="adm-uploader-grid"
        :class="{ 'is-dragover': dragging }"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="onDragLeave"
        @drop.prevent="onDrop"
      >
        <div v-for="(item, idx) in items" :key="item._key || item.file_path || idx" class="adm-uploader-cell">
          <div class="adm-uploader-box is-grid">
            <el-image
              :src="item.file_path"
              :preview-src-list="previewList"
              :initial-index="idx"
              preview-teleported
              fit="cover"
              class="adm-uploader-preview"
              alt="资产图片"
            />
            <span class="adm-uploader-zoom" title="点击放大预览">
              <el-icon :size="12"><ZoomIn /></el-icon>
            </span>
            <button type="button" class="adm-uploader-remove" title="移除图片" @click.stop="removeItem(idx)">
              <el-icon :size="12"><Close /></el-icon>
            </button>
          </div>
        </div>

        <el-upload
          class="adm-uploader-cell"
          action="/api/upload"
          :headers="uploadHeaders"
          accept=".png,.jpg,.jpeg"
          :show-file-list="false"
          :before-upload="beforeUpload"
          :on-success="onUploadSuccess"
          :on-error="onUploadError"
        >
          <div class="adm-uploader-box is-grid is-add">
            <el-icon :size="18"><Plus /></el-icon>
            <span>添加图片</span>
          </div>
        </el-upload>
        <div v-if="dragging" class="adm-uploader-drop-tip">松开鼠标上传图片</div>
      </div>
      <p v-if="tip" class="adm-uploader-tip">{{ tip }} · 可拖拽图片到此处，仅 png / jpg</p>
    </template>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Camera, Close, Picture, Plus, ZoomIn } from '@element-plus/icons-vue'
import { api } from '../../api'
import { readToken } from '../../utils/session'

const props = defineProps({
  /** 单图模式：当前图片地址 */
  src: { type: String, default: '' },
  /** 多图模式：图片列表，元素形如 { file_path, sort } */
  items: { type: Array, default: () => [] },
  /** single = 单图替换；list = 多图网格 */
  mode: { type: String, default: 'single' },
  /** circle = 圆形头像；square = 方形圆角 */
  shape: { type: String, default: 'square' },
  size: { type: Number, default: 72 },
  tip: { type: String, default: '' },
  fallbackIcon: { type: [Object, Function], default: null }
})

const emit = defineEmits(['update:src', 'update:items'])

const uploadHeaders = computed(() => {
  const token = readToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
})

const boxSize = computed(() => `${props.size}px`)
const resolvedFallback = computed(() => props.fallbackIcon || Picture)
const previewList = computed(() => props.items.map((i) => i.file_path).filter(Boolean))
const dragging = ref(false)

const ALLOWED_EXT = /\.(png|jpe?g)$/i

function isAllowed(file) {
  return ALLOWED_EXT.test(file?.name || '')
}

function beforeUpload(file) {
  if (!isAllowed(file)) {
    ElMessage.error('仅支持 png / jpg 格式图片')
    return false
  }
  return true
}

function onUploadSuccess(res) {
  if (!res || !res.url) {
    ElMessage.error('上传失败，请重试')
    return
  }
  if (props.mode === 'single') {
    emit('update:src', res.url)
  } else {
    appendItems([res.url])
  }
  ElMessage.success('上传成功')
}

function onUploadError() {
  ElMessage.error('上传失败，请重试')
}

function appendItems(urls) {
  if (!urls.length) return
  const next = [...props.items]
  for (const url of urls) {
    next.push({ _key: `${Date.now()}-${Math.random()}`, file_path: url, sort: next.length })
  }
  emit('update:items', next)
}

function onDragLeave() {
  dragging.value = false
}

async function onDrop(event) {
  dragging.value = false
  const files = Array.from(event?.dataTransfer?.files || [])
  if (!files.length) return
  const valid = files.filter(isAllowed)
  if (valid.length !== files.length) {
    ElMessage.warning('已忽略非 png / jpg 格式图片')
  }
  if (!valid.length) return
  try {
    const urls = []
    for (const file of valid) {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post('/upload', form)
      if (data?.url) urls.push(data.url)
    }
    if (props.mode === 'single') {
      if (urls[0]) {
        emit('update:src', urls[0])
        ElMessage.success('上传成功')
      }
    } else {
      appendItems(urls)
      ElMessage.success(`已上传 ${urls.length} 张图片`)
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '上传失败，请重试')
  }
}

function removeItem(idx) {
  const next = props.items.filter((_, i) => i !== idx)
  emit('update:items', next)
}
</script>

<style scoped>
.adm-uploader {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
}

.adm-uploader.is-circle {
  border-radius: 999px;
}

/* 单图 */
.adm-uploader-box {
  position: relative;
  overflow: hidden;
  cursor: pointer;
  background: var(--adm-input-bg);
  border: 1px solid var(--adm-border-dark);
  display: grid;
  place-items: center;
  transition: border-color 0.18s ease, box-shadow 0.18s ease;
}

.is-circle .adm-uploader-box {
  border-radius: 999px;
}

.is-square .adm-uploader-box {
  border-radius: 14px;
}

.adm-uploader-box:hover,
.adm-uploader-box:global(.is-dragover) {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.18);
}

.adm-uploader-box img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

/* 无图占位：柔和渐变 + 内描边 */
.adm-uploader-fallback {
  width: 100%;
  height: 100%;
  display: grid;
  place-items: center;
  color: var(--adm-text-placeholder);
  background:
    radial-gradient(circle at 52% 40%, rgba(255, 255, 255, 0.72) 0 22%, transparent 23%),
    linear-gradient(145deg, rgba(255, 255, 255, 0.5), rgba(123, 163, 209, 0.1));
  box-shadow: inset 0 0 0 1px var(--adm-border-dark);
}

.adm-uploader-fallback :deep(svg) {
  width: 34%;
  height: 34%;
  min-width: 16px;
  min-height: 16px;
}

/* hover 遮罩 */
.adm-uploader-mask {
  position: absolute;
  inset: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
  background: rgba(0, 0, 0, 0.46);
  opacity: 0;
  transition: opacity 0.18s ease;
}

.adm-uploader-box:hover .adm-uploader-mask {
  opacity: 1;
}

/* 多图网格 */
.adm-uploader-grid {
  position: relative;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(84px, 1fr));
  gap: 10px;
  width: 100%;
  padding: 4px;
  border: 1px dashed transparent;
  border-radius: 14px;
  transition: border-color 0.18s ease, background-color 0.18s ease;
}

.adm-uploader-grid.is-dragover {
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
}

.adm-uploader-cell {
  display: block;
  width: 100%;
}
.adm-uploader-grid :deep(.el-upload) {
  display: block;
  width: 100%;
}

.adm-uploader-box.is-grid {
  width: 100%;
  aspect-ratio: 1 / 1;
  border-radius: 12px;
}

.adm-uploader-preview {
  width: 100%;
  height: 100%;
  display: block;
}

.adm-uploader-zoom {
  position: absolute;
  left: 5px;
  bottom: 5px;
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  border-radius: 6px;
  color: #fff;
  background: rgba(15, 23, 42, 0.56);
  opacity: 0;
  pointer-events: none;
  transition: opacity 0.18s ease;
}

.adm-uploader-cell:hover .adm-uploader-zoom {
  opacity: 1;
}

.adm-uploader-drop-tip {
  position: absolute;
  inset: 0;
  display: grid;
  place-items: center;
  border-radius: 14px;
  color: var(--el-color-primary);
  font-size: 13px;
  font-weight: 700;
  background: var(--adm-active-bg);
  pointer-events: none;
}

.adm-uploader-box.is-add {
  flex-direction: column;
  gap: 4px;
  color: var(--adm-text-secondary);
  font-size: 11px;
  font-weight: 600;
  border-style: dashed;
  border-color: var(--adm-border-deep);
  background: var(--adm-panel);
}

.adm-uploader-box.is-add:hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
}

.adm-uploader-remove {
  position: absolute;
  top: 4px;
  right: 4px;
  width: 20px;
  height: 20px;
  display: grid;
  place-items: center;
  padding: 0;
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  color: #fff;
  background: rgba(15, 23, 42, 0.62);
  opacity: 0;
  transition: opacity 0.18s ease, background-color 0.18s ease;
}

.adm-uploader-cell:hover .adm-uploader-remove {
  opacity: 1;
}

.adm-uploader-remove:hover {
  background: var(--el-color-danger);
}

.adm-uploader-tip {
  margin: 0;
  font-size: 12px;
  line-height: 1.5;
  color: var(--adm-text-secondary);
}
</style>
