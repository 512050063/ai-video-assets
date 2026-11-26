<script setup>
/* 抖音风格社交图标：心形（点赞）/ 气泡（评论）/ 星形（收藏）/ 箭头（转发）
 * 用内联 SVG 绘制，Element Plus 图标库没有心形与实心气泡。
 */
const props = defineProps({
  name: { type: String, required: true },
  size: { type: Number, default: 13 }
})

// path 数据：viewBox 统一 0 0 24 24
const PATHS = {
  // 心形（抖音点赞）
  heart:
    'M12 21.35l-1.45-1.32C5.4 15.36 2 12.28 2 8.5 2 5.42 4.42 3 7.5 3c1.74 0 3.41.81 4.5 2.09C13.09 3.81 14.76 3 16.5 3 19.58 3 22 5.42 22 8.5c0 3.78-3.4 6.86-8.55 11.54L12 21.35z',
  // 气泡（评论）
  comment:
    'M12 3C6.48 3 2 6.58 2 11c0 2.38 1.19 4.47 3 6v4l4.5-2.5c.8.17 1.63.25 2.5.25 5.52 0 10-3.58 10-8S17.52 3 12 3z',
  // 星形（收藏）
  star:
    'M12 2.5l2.9 6.02 6.35.92-4.6 4.48 1.09 6.33L12 17.3l-5.74 3.02 1.09-6.33-4.6-4.48 6.35-.92L12 2.5z',
  // 箭头（转发）
  share:
    'M13.2 4.2L4.6 11.4c-.7.6-.7 1.6 0 2.2l2.3 1.9 1.5-4.3 4.8-3.1-4.2 5.6 5.6 4.6c.7.6 1.7.1 1.7-.8V5.6c0-.8-.8-1.9-1.1-1.4z',
  // 眼睛（播放量）
  play:
    'M12 5C6.5 5 2.7 9.1 1.5 12c1.2 2.9 5 7 10.5 7s9.3-4.1 10.5-7C21.3 9.1 17.5 5 12 5zm0 11.5A4.5 4.5 0 1 1 12 7.5a4.5 4.5 0 0 1 0 9zm0-7A2.5 2.5 0 1 0 12 14a2.5 2.5 0 0 0 0-5z'
}
</script>

<template>
  <svg
    class="dy-icon"
    :width="props.size"
    :height="props.size"
    viewBox="0 0 24 24"
    fill="currentColor"
    aria-hidden="true"
  >
    <path :d="PATHS[props.name] || ''" />
  </svg>
</template>

<style scoped>
.dy-icon {
  display: inline-block;
  vertical-align: -0.15em;
  flex-shrink: 0;
}
</style>
