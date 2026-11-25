<script setup>
/* 表格内状态标签：点击后弹出可选状态，直接切换。
 * options: [{ value, label, type }]，type 为 Element Plus tag 类型。
 */
import { computed } from 'vue'
import { ArrowDown } from '@element-plus/icons-vue'

const props = defineProps({
  status: { type: String, default: '' },
  options: { type: Array, required: true },
  typeFn: { type: Function, default: null },
  disabled: { type: Boolean, default: false }
})
const emit = defineEmits(['change'])

const tagType = computed(() => {
  if (props.typeFn) return props.typeFn(props.status)
  const hit = props.options.find((o) => o.value === props.status)
  return hit ? hit.type : 'info'
})

function onCommand(value) {
  if (value !== props.status) emit('change', value)
}
</script>

<template>
  <el-dropdown v-if="!disabled" trigger="click" @command="onCommand">
    <button type="button" class="status-tag-btn" title="点击修改状态">
      <el-tag :type="tagType" size="small" effect="light">{{ status }}</el-tag>
      <el-icon class="status-tag-caret" :size="11"><ArrowDown /></el-icon>
    </button>
    <template #dropdown>
      <el-dropdown-menu>
        <el-dropdown-item
          v-for="o in options"
          :key="o.value"
          :command="o.value"
          :disabled="o.value === status"
        >
          <el-tag :type="o.type" size="small" effect="light">{{ o.label }}</el-tag>
        </el-dropdown-item>
      </el-dropdown-menu>
    </template>
  </el-dropdown>
  <el-tag v-else :type="tagType" size="small" effect="light">{{ status }}</el-tag>
</template>

<style scoped>
.status-tag-btn {
  display: inline-flex;
  align-items: center;
  gap: 2px;
  padding: 0;
  border: 0;
  background: transparent;
  cursor: pointer;
  line-height: 1;
}
.status-tag-caret {
  color: var(--adm-text-placeholder, #a8abb2);
}
</style>
