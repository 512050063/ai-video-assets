<template>
  <el-drawer
    :model-value="modelValue"
    direction="rtl"
    :size="size"
    :with-header="false"
    class="adm-drawer"
    @update:model-value="(v) => emit('update:modelValue', v)"
  >
    <!-- 抽屉头部：图标徽章 + 标题 + 副标题（对标 ozon 商品详情抽屉） -->
    <div class="adm-drawer-head">
      <div class="adm-drawer-head-icon">
        <el-icon :size="18"><component :is="icon" /></el-icon>
      </div>
      <div class="adm-drawer-head-text">
        <div class="adm-drawer-head-title">{{ title }}</div>
        <div v-if="subtitle" class="adm-drawer-head-sub">{{ subtitle }}</div>
      </div>
      <button class="adm-drawer-close" type="button" title="关闭" @click="close">
        <el-icon :size="16"><Close /></el-icon>
      </button>
    </div>

    <div class="adm-drawer-body">
      <!-- 顶部封面 / 媒体区 -->
      <div v-if="cover || videoFile" class="adm-drawer-media">
        <video
          v-if="videoFile"
          class="adm-drawer-video"
          :src="videoFile"
          controls
          preload="metadata"
        />
        <img v-else-if="cover" class="adm-drawer-cover" :src="cover" :alt="title" />
      </div>

      <!-- 信息区块 -->
      <section v-for="(sec, si) in sections" :key="si" class="adm-drawer-section">
        <h4 class="adm-drawer-section-title">
          <span class="adm-drawer-bar" :class="`is-${sec.tone || 'primary'}`" />
          {{ sec.title }}
        </h4>
        <div class="adm-drawer-grid">
          <div v-for="(item, ii) in sec.items" :key="ii" class="adm-drawer-field">
            <span class="adm-drawer-label">{{ item.label }}</span>
            <span class="adm-drawer-value" :class="{ 'is-empty': item.empty }">
              <template v-if="item.html"><span v-html="item.html" /></template>
              <template v-else>{{ item.value ?? '—' }}</template>
            </span>
          </div>
        </div>
      </section>

      <!-- 自定义插槽 -->
      <div v-if="$slots.default" class="adm-drawer-extra">
        <slot />
      </div>
    </div>

    <template v-if="$slots.footer" #footer>
      <div class="adm-drawer-footer">
        <slot name="footer" />
      </div>
    </template>
  </el-drawer>
</template>

<script setup>
import { onBeforeUnmount, onMounted } from 'vue'
import { Close } from '@element-plus/icons-vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '详情' },
  subtitle: { type: String, default: '' },
  icon: { type: [Object, Function, String], default: null },
  size: { type: String, default: '58%' },
  cover: { type: String, default: '' },
  videoFile: { type: String, default: '' },
  /** sections: [{ title, tone, items: [{ label, value, html, empty }] }] */
  sections: { type: Array, default: () => [] }
})

const emit = defineEmits(['update:modelValue'])

function close() {
  emit('update:modelValue', false)
}

// ESC 关闭：抽屉内元素可能未持有焦点，显式在 document 上兜底监听
function onKeydown(e) {
  if (e.key === 'Escape' && props.modelValue) close()
}

onMounted(() => document.addEventListener('keydown', onKeydown))
onBeforeUnmount(() => document.removeEventListener('keydown', onKeydown))
</script>

<style scoped>
.adm-drawer :deep(.el-drawer) {
  background: var(--adm-bg);
}
.adm-drawer :deep(.el-drawer__body) {
  padding: 0;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 头部 */
.adm-drawer-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  border-bottom: 1px solid var(--adm-border);
  background: var(--adm-surface);
  flex: 0 0 auto;
}
.adm-drawer-head-icon {
  width: 36px;
  height: 36px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--adm-blue);
  background: var(--adm-blue-bg);
  flex: 0 0 auto;
}
.adm-drawer-head-text {
  min-width: 0;
  flex: 1;
}
.adm-drawer-head-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--adm-text-primary);
  line-height: 1.3;
}
.adm-drawer-head-sub {
  font-size: 12px;
  color: var(--adm-text-muted);
  margin-top: 2px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.adm-drawer-close {
  width: 28px;
  height: 28px;
  border: none;
  border-radius: 8px;
  background: transparent;
  color: var(--adm-text-muted);
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background-color 0.15s ease, color 0.15s ease;
}
.adm-drawer-close:hover {
  background: var(--adm-hover-bg);
  color: var(--adm-text-primary);
}

/* 主体 */
.adm-drawer-body {
  flex: 1 1 auto;
  overflow-y: auto;
  padding: 16px 20px 24px;
}

/* 媒体区 */
.adm-drawer-media {
  margin-bottom: 16px;
  border-radius: 12px;
  overflow: hidden;
  background: var(--adm-surface-sunken);
  border: 1px solid var(--adm-border);
}
.adm-drawer-cover {
  display: block;
  width: 100%;
  max-height: 260px;
  object-fit: cover;
}
.adm-drawer-video {
  display: block;
  width: 100%;
  max-height: 320px;
  background: #000;
}

/* 区块 */
.adm-drawer-section {
  background: var(--adm-surface-sunken);
  border: 1px solid var(--adm-border);
  border-radius: 12px;
  padding: 14px 16px;
  margin-bottom: 12px;
}
.adm-drawer-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px;
  font-size: 13px;
  font-weight: 600;
  color: var(--adm-text-primary);
}
.adm-drawer-bar {
  width: 3px;
  height: 14px;
  border-radius: 2px;
  background: var(--adm-blue);
}
.adm-drawer-bar.is-coral { background: var(--adm-coral); }
.adm-drawer-bar.is-mint { background: var(--adm-mint); }
.adm-drawer-bar.is-amber { background: var(--adm-amber); }
.adm-drawer-bar.is-lilac { background: var(--adm-lilac); }

.adm-drawer-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px 20px;
}
@media (max-width: 900px) {
  .adm-drawer-grid { grid-template-columns: minmax(0, 1fr); }
}
.adm-drawer-field {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 12px;
  min-width: 0;
}
.adm-drawer-label {
  font-size: 12px;
  color: var(--adm-text-muted);
  flex: 0 0 auto;
}
.adm-drawer-value {
  font-size: 13px;
  color: var(--adm-text-primary);
  text-align: right;
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.adm-drawer-value.is-empty {
  color: var(--adm-text-muted);
}

.adm-drawer-extra {
  margin-top: 4px;
}

.adm-drawer-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  width: 100%;
}
</style>
