<template>
  <div
    :class="['adm-grid-skeleton', { 'is-assets': variant === 'assets' }]"
    :style="{ '--gs-cols': cols }"
    aria-busy="true"
    aria-label="数据加载中"
  >
    <div v-if="variant !== 'assets'" class="gs-row is-head">
      <span
        v-for="c in cols"
        :key="'head-' + c"
        class="gs-cell is-head"
        :style="{ width: headWidth(c) }"
      />
    </div>
    <div v-for="r in rows" :key="'row-' + r" class="gs-row">
      <span
        v-for="c in cols"
        :key="'cell-' + r + '-' + c"
        :class="['gs-cell', { 'is-thumb': c === 1 && thumb }]"
        :style="cellStyle(c)"
      />
    </div>
    <span class="gs-sheen" />
  </div>
</template>

<script setup>
// 数据加载栅格骨架：与表格同构的行列占位，避免加载中空白与布局跳动。
defineProps({
  rows: { type: Number, default: 6 },
  cols: { type: Number, default: 6 },
  thumb: { type: Boolean, default: false },
  variant: { type: String, default: 'table' } // table | assets
})

const HEAD_WIDTHS = ['68%', '54%', '48%', '60%', '42%', '52%']
const CELL_WIDTHS = ['82%', '66%', '74%', '58%', '70%', '46%']

function headWidth(c) {
  return HEAD_WIDTHS[(c - 1) % HEAD_WIDTHS.length]
}
function cellStyle(c) {
  return { width: CELL_WIDTHS[(c - 1) % CELL_WIDTHS.length] }
}
</script>
