<template>
  <el-select
    v-model="innerValue"
    multiple
    filterable
    allow-create
    clearable
    default-first-option
    :reserve-keyword="false"
    :placeholder="placeholder"
    :disabled="disabled"
    class="adm-tag-select"
    @change="handleChange"
  >
    <el-option
      v-for="opt in options"
      :key="opt.name"
      :label="opt.name"
      :value="opt.name"
    >
      <span class="adm-tag-opt">
        <span class="adm-tag-opt-name">#{{ opt.name }}</span>
        <span v-if="opt.usage_count" class="adm-tag-opt-count">{{ opt.usage_count }}</span>
      </span>
    </el-option>
  </el-select>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { api } from '../../api'

const props = defineProps({
  modelValue: { type: Array, default: () => [] },
  placeholder: { type: String, default: '输入话题标签回车创建，或从话题标签库选择' },
  disabled: { type: Boolean, default: false }
})

const emit = defineEmits(['update:modelValue', 'change'])

const options = ref([])

const innerValue = computed({
  get: () => props.modelValue || [],
  set: (v) => emit('update:modelValue', v)
})

async function loadOptions() {
  try {
    const { data } = await api.get('/tags/options')
    options.value = Array.isArray(data) ? data : []
  } catch (e) {
    options.value = []
  }
}

function handleChange(val) {
  emit('change', val)
}

onMounted(loadOptions)
// 打开弹窗时刷新话题标签库，保证新登记的话题标签能立即选到
watch(
  () => props.modelValue,
  () => loadOptions(),
  { deep: true }
)

defineExpose({ reload: loadOptions })
</script>

<style scoped>
.adm-tag-select {
  width: 100%;
}
.adm-tag-opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}
.adm-tag-opt-count {
  font-size: 11px;
  color: var(--adm-text-muted);
  font-variant-numeric: tabular-nums;
}
</style>
