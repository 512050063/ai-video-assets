<script setup>
/* 抖音风格社交图标：播放量（描边三角）/ 喜欢 / 评论 / 收藏 / 转发（弯头箭头）/ 时长（时钟）
 * 用内联 SVG 绘制，Element Plus 图标库没有对应风格图标。
 */
const props = defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 13 }
})

// 统一 viewBox 0 0 24 24；stroke 为描边图标（播放/时长），其余为实心图标
const ICONS = {
  // 播放量：圆角三角形轮廓（替换原眼睛图标）
  play: {
    d: 'M8.6 5.6 19 12 8.6 18.4Z',
    stroke: true
  },
  // 喜欢（抖音心形）
  heart: {
    d: 'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z'
  },
  // 评论（气泡）
  comment: {
    d: 'M12 3C6.48 3 2 6.58 2 11c0 2.38 1.19 4.47 3 6v4l4.5-2.5c.8.17 1.63.25 2.5.25 5.52 0 10-3.58 10-8S17.52 3 12 3z'
  },
  // 收藏（星形）
  star: {
    d: 'M12 2.5l2.9 6.02 6.35.92-4.6 4.48 1.09 6.33L12 17.3l-5.74 3.02 1.09-6.33-4.6-4.48 6.35-.92L12 2.5z'
  },
  // 转发：圆头弯尾右箭头
  share: {
    d: 'M13 5l7 7-7 7v-4.2H9.5C6 13.8 3.7 15.7 2.5 19c.6-5.2 3.5-8 7.8-8H13V5z'
  },
  // 时长：简洁时钟（表盘 + 指针）
  duration: {
    d: 'M12 3a9 9 0 1 0 0 18 9 9 0 0 0 0-18Z',
    stroke: true,
    extra: ['M12 7.2V12l3.4 2']
  }
}

const icon = () => ICONS[props.name] || { d: '' }
</script>

<template>
  <svg
    class="dy-icon"
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    :fill="icon().stroke ? 'none' : 'currentColor'"
    :stroke="icon().stroke ? 'currentColor' : 'none'"
    :stroke-width="icon().stroke ? 2.2 : undefined"
    stroke-linejoin="round"
    stroke-linecap="round"
    aria-hidden="true"
  >
    <path :d="icon().d" />
    <path v-for="(p, i) in icon().extra || []" :key="i" :d="p" />
  </svg>
</template>

<style scoped>
.dy-icon {
  display: inline-block;
  vertical-align: -0.15em;
  flex-shrink: 0;
}
</style>
