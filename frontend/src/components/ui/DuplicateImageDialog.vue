<template>
  <Teleport to="body">
    <div v-if="modelValue" class="dup-overlay" @click.self="cancel">
      <div class="dup-card" role="dialog" aria-modal="true" aria-label="检测到重复图片">
        <div class="dup-icon"><el-icon :size="24"><component :is="WarningFilled" /></el-icon></div>
        <h3 class="dup-title">检测到重复图片</h3>
        <p class="dup-message">
          已存在同名资产「{{ originalName }}」，请选择处理方式。
        </p>

        <div class="dup-field">
          <label>名称</label>
          <el-input
            v-model="newName"
            size="default"
            placeholder="输入新名称"
            @keyup.enter="choose('rename')"
          />
          <span class="dup-field-hint">改名保存会用此名称新建一个资产</span>
        </div>

        <div class="dup-actions">
          <button type="button" class="dup-btn is-primary is-rename" :disabled="!newName.trim()" @click="choose('rename')">
            改名保存
          </button>
          <button type="button" class="dup-btn is-overwrite" @click="choose('overwrite')">
            覆盖原资产
          </button>
          <button type="button" class="dup-btn is-copy" @click="choose('copy')">
            创建副本
          </button>
          <button type="button" class="dup-btn is-cancel" @click="cancel">取消上传</button>
        </div>
        <p class="dup-footnote">覆盖会替换原资产的图片；创建副本会以「{{ copyName }}」新建。</p>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { WarningFilled } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  originalName: { type: String, default: '' },
  copyName: { type: String, default: '' }
})
const emit = defineEmits(['update:modelValue', 'choose', 'cancel'])

const newName = ref('')

watch(() => props.modelValue, (open) => {
  if (open) newName.value = ''
})

function choose(action) {
  const name = action === 'rename' ? (newName.value || '').trim() : ''
  if (action === 'rename' && !name) return
  emit('update:modelValue', false)
  emit('choose', { action, name })
}

function cancel() {
  emit('update:modelValue', false)
  emit('cancel')
}
</script>

<style scoped>
.dup-overlay {
  position: fixed; inset: 0; z-index: 3000;
  display: flex; align-items: center; justify-content: center;
  background: rgba(15, 23, 42, 0.45); backdrop-filter: blur(2px);
}
.dup-card {
  width: 420px; max-width: calc(100vw - 32px);
  background: var(--adm-surface-solid, #fff); border-radius: 16px;
  padding: 24px; box-shadow: 0 20px 60px rgba(0, 0, 0, 0.2);
}
.dup-icon {
  width: 44px; height: 44px; border-radius: 12px; display: grid; place-items: center;
  color: #e6a23c; background: rgba(230, 162, 60, 0.12); margin-bottom: 14px;
}
.dup-title { margin: 0 0 8px; font-size: 18px; font-weight: 600; color: var(--adm-text-primary, #303133); }
.dup-message { margin: 0 0 16px; font-size: 13px; line-height: 1.6; color: var(--adm-text-secondary, #606266); word-break: break-all; }
.dup-field label { display: block; font-size: 13px; font-weight: 600; color: var(--adm-text-primary, #303133); margin-bottom: 6px; }
.dup-field-hint { display: block; font-size: 11px; color: var(--adm-text-secondary, #909399); margin-top: 6px; }
.dup-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-top: 18px; }
.dup-btn {
  border: 1px solid var(--adm-border, #dcdfe6); border-radius: 8px; padding: 9px 12px;
  font-size: 13px; cursor: pointer; background: var(--adm-panel, #f5f7fa);
  color: var(--adm-text-primary, #303133); transition: all 0.15s ease;
}
.dup-btn:hover:not(:disabled) { border-color: var(--el-color-primary); color: var(--el-color-primary); }
.dup-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.dup-btn.is-primary { background: var(--el-color-primary); border-color: var(--el-color-primary); color: #fff; }
.dup-btn.is-primary:hover:not(:disabled) { opacity: 0.85; color: #fff; }
.dup-btn.is-cancel { grid-column: 1 / -1; }
.dup-footnote { margin: 14px 0 0; font-size: 11px; line-height: 1.6; color: var(--adm-text-secondary, #909399); }
</style>
