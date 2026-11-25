<template>
  <div class="adm-video-uploader">
    <!-- 已上传：展示文件信息 + 预览 + 移除 -->
    <div v-if="src" class="video-box">
      <video class="video-preview" :src="src" preload="metadata" muted @click="previewVisible = true" />
      <div class="video-meta">
        <span class="video-name" :title="fileName">{{ fileName }}</span>
        <div class="video-actions">
          <el-button link type="primary" size="small" @click="previewVisible = true">预览</el-button>
          <el-button link type="danger" size="small" @click="clear">移除</el-button>
        </div>
      </div>
    </div>

    <!-- 未上传：拖拽 / 选择文件 -->
    <div v-else class="video-drop" @click="pick">
      <el-icon :size="20"><UploadFilled /></el-icon>
      <span class="video-drop-text">{{ uploading ? '上传中...' : '点击上传视频文件' }}</span>
      <span class="video-drop-tip">支持 mp4 / mov / webm / avi</span>
      <input
        ref="fileInput"
        type="file"
        class="video-input"
        accept="video/mp4,video/*"
        @change="onPicked"
      />
    </div>

    <el-dialog v-model="previewVisible" width="720px" title="视频预览" align-center>
      <video v-if="src" class="video-player" :src="src" controls autoplay preload="metadata" />
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { UploadFilled } from '@element-plus/icons-vue'
import { api } from '../../api'
import { readToken } from '../../utils/session'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: '上传视频文件' }
})

const emit = defineEmits(['update:modelValue'])

const fileInput = ref(null)
const uploading = ref(false)
const previewVisible = ref(false)

const src = computed(() => props.modelValue || '')
const fileName = computed(() => {
  if (!src.value) return ''
  const parts = src.value.split('/')
  return parts[parts.length - 1]
})

function pick() {
  fileInput.value?.click()
}

async function onPicked(e) {
  const file = e.target.files?.[0]
  e.target.value = ''
  if (!file) return
  uploading.value = true
  try {
    const fd = new FormData()
    fd.append('file', file)
    const token = readToken()
    const { data } = await api.post('/upload', fd, {
      headers: token ? { Authorization: `Bearer ${token}` } : {}
    })
    emit('update:modelValue', data.url)
    ElMessage.success('视频已上传')
  } catch (err) {
    ElMessage.error(err.response?.data?.detail || '上传失败')
  } finally {
    uploading.value = false
  }
}

function clear() {
  emit('update:modelValue', '')
}
</script>

<style scoped>
.adm-video-uploader {
  width: 100%;
}
.video-box {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--adm-border);
  border-radius: 10px;
  background: var(--adm-panel-soft);
}
.video-preview {
  width: 96px;
  height: 54px;
  object-fit: cover;
  border-radius: 6px;
  background: #000;
  cursor: pointer;
  flex: 0 0 auto;
}
.video-meta {
  min-width: 0;
  flex: 1;
}
.video-name {
  display: block;
  font-size: 12.5px;
  color: var(--adm-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.video-actions {
  margin-top: 4px;
  display: flex;
  gap: 4px;
}
.video-drop {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 4px;
  height: 92px;
  border: 1px dashed var(--adm-border-dark);
  border-radius: 10px;
  color: var(--adm-text-placeholder);
  cursor: pointer;
  transition: border-color 0.15s ease, background-color 0.15s ease;
}
.video-drop:hover {
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
}
.video-drop-text {
  font-size: 13px;
  color: var(--adm-text-secondary);
}
.video-drop-tip {
  font-size: 11px;
}
.video-input {
  display: none;
}
.video-player {
  width: 100%;
  max-height: 62vh;
  border-radius: 10px;
  background: #000;
}
</style>
