<template>
  <div class="trend-chart">
    <div class="trend-legend">
      <span v-for="s in series" :key="s.name" class="trend-legend-item">
        <i class="trend-dot" :style="{ background: s.color }" />
        {{ s.name }}
      </span>
    </div>
    <svg class="trend-svg" :viewBox="`0 0 ${width} ${height}`" preserveAspectRatio="none" role="img" aria-label="趋势图">
      <defs>
        <linearGradient
          v-for="(s, i) in series"
          :key="'g' + i"
          :id="`trend-grad-${uid}-${i}`"
          x1="0"
          y1="0"
          x2="0"
          y2="1"
        >
          <stop offset="0%" :stop-color="s.color" stop-opacity="0.28" />
          <stop offset="100%" :stop-color="s.color" stop-opacity="0" />
        </linearGradient>
      </defs>

      <g class="trend-grid">
        <template v-for="i in 5" :key="'grid' + i">
          <line :x1="pad.left" :x2="width - pad.right" :y1="gridY(i)" :y2="gridY(i)" />
          <text :x="pad.left - 6" :y="gridY(i) + 3" text-anchor="end">{{ formatValue((maxValue * (5 - i)) / 4) }}</text>
        </template>
      </g>

      <g v-for="(s, si) in series" :key="s.name">
        <path
          v-if="si === 0"
          class="trend-area"
          :d="areaPath(s.values)"
          :fill="`url(#trend-grad-${uid}-${si})`"
        />
        <path
          class="trend-line"
          :d="linePath(s.values)"
          :stroke="s.color"
          pathLength="1"
          :style="{ animationDelay: `${si * 0.16}s` }"
        />
        <circle
          v-for="(v, i) in s.values"
          :key="`${s.name}-${i}`"
          class="trend-point"
          :cx="pointX(i)"
          :cy="pointY(v)"
          :r="i === s.values.length - 1 ? 3.6 : 2"
          :fill="s.color"
        >
          <title>{{ labels[i] }} · {{ s.name }} {{ v }}</title>
        </circle>
      </g>

      <text
        v-for="(label, i) in labels"
        :key="'x' + i"
        class="trend-x-label"
        :x="pointX(i)"
        :y="height - 5"
        text-anchor="middle"
      >
        {{ i % 3 === 0 || i === labels.length - 1 ? label : '' }}
      </text>
    </svg>
  </div>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  labels: { type: Array, default: () => [] },
  series: { type: Array, default: () => [] },
  height: { type: Number, default: 176 }
})

const width = 640
const pad = { left: 38, right: 12, top: 12, bottom: 26 }
const uid = Math.random().toString(36).slice(2, 8)

const allValues = computed(() => props.series.flatMap((s) => s.values || []))
const maxValue = computed(() => {
  const peak = Math.max(1, ...allValues.value)
  return Math.ceil(peak / 4) * 4
})

function formatValue(v) {
  if (v >= 10000) return `${(v / 10000).toFixed(1)}万`
  if (v >= 1000) return `${(v / 1000).toFixed(1)}k`
  return String(Math.round(v))
}
function pointX(i) {
  const n = Math.max(1, props.labels.length - 1)
  return pad.left + (i / n) * (width - pad.left - pad.right)
}
function pointY(v) {
  const inner = props.height - pad.top - pad.bottom
  return pad.top + (1 - (v || 0) / maxValue.value) * inner
}
function gridY(i) {
  return pad.top + ((i - 1) / 4) * (props.height - pad.top - pad.bottom)
}
function linePath(values) {
  if (!values?.length) return ''
  const pts = values.map((v, i) => [pointX(i), pointY(v)])
  let d = `M ${pts[0][0]} ${pts[0][1]}`
  for (let i = 1; i < pts.length; i++) {
    const prev = pts[i - 1]
    const cur = pts[i]
    const mid = (prev[0] + cur[0]) / 2
    d += ` C ${mid} ${prev[1]}, ${mid} ${cur[1]}, ${cur[0]} ${cur[1]}`
  }
  return d
}
function areaPath(values) {
  if (!values?.length) return ''
  const bottom = props.height - pad.bottom
  return `${linePath(values)} L ${pointX(values.length - 1)} ${bottom} L ${pointX(0)} ${bottom} Z`
}
</script>

<style scoped>
.trend-chart {
  min-width: 0;
}
.trend-legend {
  display: flex;
  align-items: center;
  gap: 14px;
  margin-bottom: 2px;
}
.trend-legend-item {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  font-size: 11.5px;
  color: var(--adm-text-secondary);
}
.trend-dot {
  width: 7px;
  height: 7px;
  border-radius: 50%;
  box-shadow: 0 0 0 3px rgba(91, 143, 249, 0.12);
}
.trend-svg {
  width: 100%;
  height: 176px;
  display: block;
  overflow: visible;
}
.trend-grid line {
  stroke: var(--adm-border);
  stroke-width: 1;
  stroke-dasharray: 3 4;
}
.trend-grid text,
.trend-x-label {
  fill: var(--adm-text-placeholder);
  font-size: 9.5px;
}
.trend-line {
  fill: none;
  stroke-width: 2.4;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-dasharray: 1;
  stroke-dashoffset: 1;
  animation: trend-draw 1.25s cubic-bezier(0.22, 0.72, 0.3, 1) forwards;
}
.trend-area {
  opacity: 0;
  animation: trend-fade 1.1s ease 0.35s forwards;
}
.trend-point {
  opacity: 0;
  animation: trend-fade 0.6s ease 0.9s forwards;
}
@keyframes trend-draw {
  to { stroke-dashoffset: 0; }
}
@keyframes trend-fade {
  to { opacity: 1; }
}
</style>
