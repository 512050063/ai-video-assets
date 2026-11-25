<template>
  <el-dialog
    v-model="visible"
    :width="width"
    :title="title"
    align-center
    :close-on-click-modal="false"
    destroy-on-close
  >
    <template #header>
      <DialogHeader :icon="icon" :title="title" :sub="subtitle" :tone="tone" />
    </template>

    <el-input
      v-if="searchable"
      v-model="keyword"
      placeholder="搜索名称"
      clearable
      style="margin-bottom: 12px"
    >
      <template #prefix><el-icon><Search /></el-icon></template>
    </el-input>

    <div v-loading="loading" class="picker-list">
      <button
        v-for="item in filtered"
        :key="item.id"
        type="button"
        class="picker-item"
        :class="{ 'is-active': selectedId === item.id }"
        @click="selectedId = item.id"
      >
        <img v-if="item.cover" :src="item.cover" class="picker-cover" :alt="item.title" />
        <span v-else class="picker-cover is-empty">—</span>
        <span class="picker-text">
          <span class="picker-title" :title="item.title">{{ item.title || '未命名' }}</span>
          <span v-if="item.subtitle" class="picker-sub" :title="item.subtitle">{{ item.subtitle }}</span>
        </span>
        <el-icon v-if="selectedId === item.id" class="picker-check"><CircleCheckFilled /></el-icon>
      </button>

      <div v-if="!loading && !filtered.length" class="picker-empty">
        <el-icon :size="26"><DocumentDelete /></el-icon>
        <span>{{ emptyText }}</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="confirming" :disabled="!selectedId" @click="confirm">
        确认{{ confirmText }}
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { CircleCheckFilled, DocumentDelete, Search } from '@element-plus/icons-vue'
import DialogHeader from './DialogHeader.vue'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  title: { type: String, default: '选择来源' },
  subtitle: { type: String, default: '' },
  icon: { type: [Object, Function, String], default: null },
  tone: { type: String, default: 'primary' },
  width: { type: String, default: '520px' },
  /** [{ id, title, subtitle, cover }] */
  items: { type: Array, default: () => [] },
  loading: { type: Boolean, default: false },
  confirming: { type: Boolean, default: false },
  searchable: { type: Boolean, default: true },
  emptyText: { type: String, default: '暂无可选项' },
  confirmText: { type: String, default: '' }
})

const emit = defineEmits(['update:modelValue', 'confirm'])

const keyword = ref('')
const selectedId = ref(null)

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const filtered = computed(() => {
  const kw = keyword.value.trim().toLowerCase()
  if (!kw) return props.items
  return props.items.filter((i) =>
    [i.title, i.subtitle].some((v) => String(v || '').toLowerCase().includes(kw))
  )
})

watch(
  () => props.modelValue,
  (v) => {
    if (v) {
      keyword.value = ''
      selectedId.value = null
    }
  }
)

function confirm() {
  if (!selectedId.value) return
  const item = props.items.find((i) => i.id === selectedId.value)
  emit('confirm', item)
}
</script>

<style scoped>
.picker-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-height: 46vh;
  min-height: 120px;
  overflow-y: auto;
  padding-right: 4px;
}
.picker-item {
  display: flex;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 8px 10px;
  border: 1px solid var(--adm-border);
  border-radius: 10px;
  background: var(--adm-panel-soft);
  cursor: pointer;
  text-align: left;
  transition: border-color 0.16s ease, background-color 0.16s ease;
}
.picker-item:hover {
  border-color: var(--el-color-primary-light-5);
}
.picker-item.is-active {
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
}
.picker-cover {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  border-radius: 8px;
  object-fit: cover;
  background: var(--adm-surface-sunken);
  border: 1px solid var(--adm-border);
}
.picker-cover.is-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--adm-text-placeholder);
  font-size: 11px;
}
.picker-text {
  min-width: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.picker-title {
  font-size: 13px;
  color: var(--adm-text-primary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker-sub {
  font-size: 11.5px;
  color: var(--adm-text-placeholder);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.picker-check {
  color: var(--el-color-primary);
  flex-shrink: 0;
}
.picker-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 30px 0;
  color: var(--adm-text-placeholder);
  font-size: 13px;
}
</style>
