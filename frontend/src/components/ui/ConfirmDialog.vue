<template>
  <Teleport to="body">
    <div v-if="modelValue" class="adm-confirm-overlay" @click.self="closeOnOverlay && handleCancel()">
      <div class="adm-confirm-card" role="dialog" aria-modal="true" :aria-label="title">
        <div :class="['adm-confirm-icon', `is-${variant}`]">
          <el-icon :size="24"><component :is="iconComponent" /></el-icon>
        </div>

        <h3 class="adm-confirm-title">{{ title }}</h3>
        <p class="adm-confirm-message">{{ message }}</p>

        <div class="adm-confirm-actions">
          <button
            type="button"
            :class="['adm-confirm-btn', 'is-primary', `is-${variant}`]"
            :disabled="loading"
            @click="handleConfirm"
          >
            {{ loading ? loadingText : confirmText }}
          </button>
          <button
            type="button"
            class="adm-confirm-btn is-cancel"
            :disabled="loading"
            @click="handleCancel"
          >
            {{ cancelText }}
          </button>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, watch } from 'vue'
import { CircleCheck, Delete, InfoFilled, WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '确认删除' },
  message: { type: String, default: '删除后无法恢复，确定继续吗？' },
  confirmText: { type: String, default: '删除' },
  cancelText: { type: String, default: '取消' },
  loadingText: { type: String, default: '处理中...' },
  loading: { type: Boolean, default: false },
  variant: { type: String, default: 'danger' },
  icon: { type: String, default: 'delete' },
  closeOnOverlay: { type: Boolean, default: true }
})

const emit = defineEmits(['update:modelValue', 'confirm', 'cancel'])

const iconComponent = computed(() => {
  if (props.icon === 'success') return CircleCheck
  if (props.icon === 'warning') return WarningFilled
  if (props.icon === 'info') return InfoFilled
  return Delete
})

function handleCancel() {
  if (props.loading) return
  emit('update:modelValue', false)
  emit('cancel')
}

function handleConfirm() {
  if (props.loading) return
  // 先关闭弹窗再执行业务：无论后续删除成功还是失败，提示消息都不会被弹窗遮挡
  emit('update:modelValue', false)
  emit('confirm')
}

// ESC 关闭
function onKeydown(e) {
  if (e.key === 'Escape' && props.modelValue) handleCancel()
}

// 打开时锁定背景滚动，避免长列表跟随滚动
watch(
  () => props.modelValue,
  (open) => {
    document.body.style.overflow = open ? 'hidden' : ''
  }
)

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => {
  document.removeEventListener('keydown', onKeydown)
  document.body.style.overflow = ''
})
</script>

<style scoped>
.adm-confirm-overlay {
  position: fixed;
  inset: 0;
  z-index: 3000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  background: rgba(61, 82, 102, 0.34);
  backdrop-filter: blur(3px);
  -webkit-backdrop-filter: blur(3px);
  animation: adm-confirm-fade 0.16s ease;
}

.adm-confirm-card {
  width: 340px;
  max-width: 100%;
  padding: 26px 30px 24px;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  background: var(--adm-surface-solid);
  border: 1px solid var(--adm-border);
  border-radius: var(--adm-radius-md);
  box-shadow: var(--adm-shadow-high);
  animation: adm-confirm-pop 0.2s cubic-bezier(0.22, 1, 0.36, 1);
}

.adm-confirm-icon {
  width: 52px;
  height: 52px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 999px;
  color: var(--el-color-danger);
  background: rgba(245, 108, 108, 0.14);
  border: 1px solid rgba(245, 108, 108, 0.26);
}

.adm-confirm-icon.is-success {
  color: var(--el-color-success);
  background: rgba(103, 194, 58, 0.14);
  border-color: rgba(103, 194, 58, 0.28);
}

.adm-confirm-icon.is-warning {
  color: var(--el-color-warning);
  background: rgba(230, 162, 60, 0.14);
  border-color: rgba(230, 162, 60, 0.28);
}

.adm-confirm-icon.is-info {
  color: var(--el-color-primary);
  background: var(--adm-active-bg);
  border-color: var(--adm-border-deep);
}

.adm-confirm-title {
  margin: 0;
  font-size: 18px;
  font-weight: 700;
  line-height: 1.3;
  color: var(--adm-text-primary);
  text-align: center;
}

.adm-confirm-message {
  margin: 0;
  max-width: 268px;
  font-size: 13px;
  line-height: 1.55;
  color: var(--adm-text-secondary);
  text-align: center;
  word-break: break-word;
}

.adm-confirm-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 4px;
}

.adm-confirm-btn {
  min-width: 96px;
  height: 36px;
  padding: 0 20px;
  border: 0;
  border-radius: 999px;
  cursor: pointer;
  font-size: 13px;
  font-weight: 600;
  line-height: 1;
  transition: transform 0.16s ease, box-shadow 0.16s ease, filter 0.16s ease, background-color 0.16s ease;
}

.adm-confirm-btn:disabled {
  cursor: not-allowed;
  opacity: 0.62;
}

.adm-confirm-btn:not(:disabled):hover {
  transform: translateY(-1px);
}

.adm-confirm-btn.is-primary {
  color: #fff;
  background: var(--el-color-danger);
  box-shadow: 0 8px 18px rgba(245, 108, 108, 0.28);
}

.adm-confirm-btn.is-primary.is-success {
  background: var(--el-color-success);
  box-shadow: 0 8px 18px rgba(103, 194, 58, 0.28);
}

.adm-confirm-btn.is-primary.is-warning {
  background: var(--el-color-warning);
  box-shadow: 0 8px 18px rgba(230, 162, 60, 0.28);
}

.adm-confirm-btn.is-primary.is-info {
  background: var(--el-color-primary);
  box-shadow: 0 8px 18px rgba(64, 158, 255, 0.28);
}

.adm-confirm-btn.is-primary:not(:disabled):hover {
  filter: brightness(0.96);
}

.adm-confirm-btn.is-cancel {
  color: var(--adm-text-regular);
  background: var(--adm-panel-strong);
  border: 1px solid var(--adm-border-dark);
}

.adm-confirm-btn.is-cancel:not(:disabled):hover {
  background: var(--adm-panel-hover);
}

@keyframes adm-confirm-fade {
  from { opacity: 0; }
  to { opacity: 1; }
}

@keyframes adm-confirm-pop {
  from { opacity: 0; transform: scale(0.94) translateY(8px); }
  to { opacity: 1; transform: scale(1) translateY(0); }
}

:global(html.dark) .adm-confirm-overlay {
  background: rgba(4, 8, 14, 0.6);
}
</style>
