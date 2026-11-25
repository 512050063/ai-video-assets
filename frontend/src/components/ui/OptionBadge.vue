<template>
  <span v-if="normalizedName" class="option-badge" :class="[`is-${mode}`, { 'is-image': !!image }]" :title="titleText">
    <template v-if="mode === 'icon'">
      <img v-if="image" class="option-badge-img" :src="image" :alt="normalizedName" />
      <span v-else class="option-badge-letter" :style="dotStyle">{{ firstChar }}</span>
    </template>
    <template v-else-if="mode === 'full'">
      <img v-if="image" class="option-badge-img" :src="image" :alt="normalizedName" />
      <span v-else class="option-badge-letter" :style="dotStyle">{{ firstChar }}</span>
      <span class="option-badge-text" :style="textStyle">{{ normalizedName }}</span>
    </template>
    <template v-else-if="mode === 'solid'">
      <span class="option-badge-solid" :style="solidStyle">{{ normalizedName }}</span>
    </template>
    <template v-else>
      <span class="option-badge-text" :style="textStyle">{{ normalizedName }}</span>
    </template>
  </span>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  name: { type: String, default: '' },
  color: { type: String, default: '#7b62c9' },
  image: { type: String, default: '' },
  display: { type: String, default: 'full' },
  size: { type: [Number, String], default: 18 }
})

const normalizedName = computed(() => (props.name || '').trim())
const mode = computed(() =>
  ['label', 'icon', 'solid'].includes(props.display) ? props.display : 'full'
)
const firstChar = computed(() => normalizedName.value.slice(0, 1))
const sizePx = computed(() => (typeof props.size === 'number' ? `${props.size}px` : props.size))
const textStyle = computed(() => ({ color: props.color || '#7b62c9' }))
const solidStyle = computed(() => ({
  backgroundColor: props.color || '#7b62c9',
  color: '#fff'
}))
const dotStyle = computed(() => ({
  backgroundColor: props.color || '#7b62c9',
  width: sizePx.value,
  height: sizePx.value
}))
const titleText = computed(() => normalizedName.value)
</script>

<style scoped>
.option-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  max-width: 100%;
  min-width: 0;
  vertical-align: middle;
}
.option-badge-text {
  font-size: 12.5px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
/* 分类标签：颜色作底色 + 白色文字 */
.option-badge-solid {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 2px 9px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1.5;
  white-space: nowrap;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
}
.option-badge-img {
  width: v-bind(sizePx);
  height: v-bind(sizePx);
  object-fit: contain;
  flex-shrink: 0;
}
.option-badge-letter {
  display: inline-grid;
  place-items: center;
  flex-shrink: 0;
  border-radius: 6px;
  color: #fff;
  font-size: 11px;
  font-weight: 600;
}
</style>
