<template>
  <div ref="rootRef" class="tag-cell-root">
    <el-tooltip
      effect="dark"
      placement="top"
      :disabled="!hiddenTags.length"
      popper-class="tag-cell-tooltip"
    >
      <template #content>
        <div class="tag-cell-tip">
          <span v-for="t in hiddenTags" :key="t" class="tag-cell-tip-item">#{{ t }}</span>
        </div>
      </template>
      <div
        ref="cellRef"
        class="adm-cell-tags tag-cell"
        :style="{ maxHeight: maxHeight + 'px' }"
      >
        <span v-for="t in visibleTags" :key="t" class="adm-tag-chip">#{{ t }}</span>
        <span v-if="hiddenTags.length" class="adm-tag-chip is-more">+{{ hiddenTags.length }}</span>
      </div>
    </el-tooltip>
    <span v-if="!tags.length" class="adm-cell-empty">{{ emptyText }}</span>

    <!-- 同宽隐藏容器：按实际列宽计算两行内能放几个标签 -->
    <div ref="measureRef" class="adm-cell-tags tag-cell tag-cell--measure" aria-hidden="true">
      <span v-for="t in tags" :key="t" class="adm-tag-chip">#{{ t }}</span>
      <span v-if="tags.length" class="adm-tag-chip is-more">+{{ tags.length }}</span>
    </div>
  </div>
</template>

<script setup>
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps({
  tags: { type: Array, default: () => [] },
  maxLines: { type: Number, default: 2 },
  emptyText: { type: String, default: '—' }
})

const CHIP_HEIGHT = 22
const CHIP_GAP = 4

const rootRef = ref(null)
const cellRef = ref(null)
const measureRef = ref(null)
const visibleCount = ref(0)

const maxHeight = computed(() => props.maxLines * CHIP_HEIGHT + (props.maxLines - 1) * CHIP_GAP)
const visibleTags = computed(() => props.tags.slice(0, visibleCount.value))
const hiddenTags = computed(() => props.tags.slice(visibleCount.value))

let observer = null

function recalc() {
  const measure = measureRef.value
  if (!measure || !props.tags.length) {
    visibleCount.value = 0
    return
  }
  const chips = Array.from(measure.querySelectorAll('.adm-tag-chip'))
  const realChips = chips.slice(0, props.tags.length)
  const moreChip = chips[props.tags.length]
  // 从多到少尝试：必须保证「可见标签 + +N」一起落在两行内
  for (let n = props.tags.length; n >= 0; n -= 1) {
    realChips.forEach((chip, i) => { chip.style.display = i < n ? '' : 'none' })
    if (moreChip) moreChip.style.display = n < props.tags.length ? '' : 'none'
    if (measure.scrollHeight <= maxHeight.value) {
      visibleCount.value = n
      return
    }
  }
  visibleCount.value = 0
}

onMounted(() => {
  nextTick(recalc)
  if (rootRef.value && typeof ResizeObserver !== 'undefined') {
    observer = new ResizeObserver(() => recalc())
    observer.observe(rootRef.value)
  }
})

onBeforeUnmount(() => {
  if (observer) {
    observer.disconnect()
    observer = null
  }
})

watch(
  () => props.tags,
  () => nextTick(recalc),
  { deep: true }
)

watch(() => props.maxLines, () => nextTick(recalc))
</script>

<style scoped>
.tag-cell-root {
  position: relative;
  width: 100%;
  min-width: 0;
}
.tag-cell {
  max-width: 100%;
  overflow: hidden;
}
.tag-cell--measure {
  position: absolute;
  left: -99999px;
  top: 0;
  visibility: hidden;
  pointer-events: none;
}
.tag-cell-tip {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
  max-width: 280px;
}
.tag-cell-tip-item {
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11.5px;
  line-height: 18px;
  color: #fff;
  background: rgba(255, 255, 255, 0.14);
}
</style>
