<template>
  <div v-if="total > 0 || alwaysShow" class="adm-pagination">
    <div class="adm-pagination-info">
      <slot name="prefix" />
      <span class="adm-pagination-summary">
        共 <span class="adm-num">{{ total }}</span> 条 · 第 <span class="adm-num">{{ page }}</span> / {{ totalPages }} 页
      </span>
      <span class="adm-page-size">
        <select
          class="adm-page-size-select"
          :value="pageSize"
          aria-label="每页条数"
          @change="onPageSizeChange"
        >
          <option v-for="n in pageSizeOptions" :key="n" :value="n">{{ n }} 条/页</option>
        </select>
      </span>
    </div>

    <div class="adm-pagination-controls">
      <button
        type="button"
        class="adm-pagination-btn is-text"
        :disabled="page <= 1"
        @click="go(page - 1)"
      >
        上一页
      </button>

      <div class="adm-pagination-pages">
        <template v-for="item in visiblePages" :key="item.key">
          <span v-if="item.type === 'ellipsis'" class="adm-pagination-ellipsis">···</span>
          <button
            v-else
            type="button"
            class="adm-pagination-btn is-page"
            :class="{ 'is-active': page === item.page }"
            @click="go(item.page)"
          >
            {{ item.page }}
          </button>
        </template>
      </div>

      <button
        type="button"
        class="adm-pagination-btn is-text"
        :disabled="page >= totalPages"
        @click="go(page + 1)"
      >
        下一页
      </button>
    </div>
  </div>
</template>

<script setup>
import { computed, watch } from 'vue'

const props = defineProps({
  /** 当前页 */
  page: { type: Number, default: 1 },
  /** 数据总条数 */
  total: { type: Number, default: 0 },
  /** 每页条数 */
  pageSize: { type: Number, default: 20 },
  /** 最多显示几个页码按钮 */
  maxVisible: { type: Number, default: 5 },
  /** 无数据时是否仍显示整条统计栏（含 prefix 里的每页条数选择） */
  alwaysShow: { type: Boolean, default: false },
  /** 每页条数可调选项 */
  pageSizeOptions: { type: Array, default: () => [10, 12, 20, 50] }
})

const emit = defineEmits(['update:page', 'update:pageSize', 'page-size-change'])

function onPageSizeChange(event) {
  const next = Number(event.target.value)
  if (!next || next === props.pageSize) return
  emit('update:pageSize', next)
  emit('page-size-change', next)
  emit('update:page', 1)
}

const totalPages = computed(() => Math.max(1, Math.ceil(props.total / props.pageSize)))

/** 窗口内可见页码：首尾页保留，中间用省略号收起 */
const visiblePages = computed(() => {
  const pages = []
  const max = props.maxVisible
  const total = totalPages.value

  if (total <= max + 2) {
    for (let i = 1; i <= total; i++) pages.push({ type: 'page', key: `p-${i}`, page: i })
    return pages
  }

  pages.push({ type: 'page', key: 'p-1', page: 1 })

  const middle = Math.max(3, max)
  let start = Math.max(2, props.page - Math.floor(middle / 2))
  let end = Math.min(total - 1, start + middle - 1)
  if (end - start + 1 < middle) start = Math.max(2, end - middle + 1)

  if (start > 2) pages.push({ type: 'ellipsis', key: 'e-left' })
  for (let i = start; i <= end; i++) pages.push({ type: 'page', key: `p-${i}`, page: i })
  if (end < total - 1) pages.push({ type: 'ellipsis', key: 'e-right' })

  pages.push({ type: 'page', key: `p-${total}`, page: total })
  return pages
})

// 数据变少导致当前页越界时，自动回到最后一页
watch(totalPages, (max) => {
  if (props.page > max) {
    emit('update:page', max)
  }
})

function go(p) {
  const next = Math.max(1, Math.min(totalPages.value, p))
  if (next === props.page) return
  emit('update:page', next)
}
</script>

<style scoped>
.adm-pagination {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  width: 100%;
  /* padding 必须计入盒模型：否则 width:100% + padding 会撑破卡片右边界，
     导致整页出现横向滚动条 */
  box-sizing: border-box;
  padding: 12px 18px;
  border-top: 1px solid var(--adm-table-line);
  background: var(--adm-panel-soft);
}

.adm-pagination-info {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 0 0 auto;
  min-width: 0;
  font-size: 12px;
  line-height: 18px;
  color: var(--adm-text-secondary);
}
.adm-pagination-summary {
  white-space: nowrap;
}
.adm-page-size {
  display: inline-flex;
  align-items: center;
}
.adm-page-size-select {
  height: 28px;
  padding: 0 22px 0 9px;
  border: 1px solid var(--adm-border-dark);
  border-radius: 8px;
  color: var(--adm-text-regular);
  background: var(--adm-panel-strong);
  font-size: 12px;
  line-height: 1;
  cursor: pointer;
  appearance: none;
  background-image: url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='10' height='6' viewBox='0 0 10 6'%3E%3Cpath d='M1 1l4 4 4-4' fill='none' stroke='%23888' stroke-width='1.4'/%3E%3C/svg%3E");
  background-repeat: no-repeat;
  background-position: right 8px center;
}
.adm-page-size-select:hover {
  border-color: var(--el-color-primary);
}

.adm-pagination-controls,
.adm-pagination-pages {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-width: 0;
}

.adm-pagination-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  height: 28px;
  padding: 0 10px;
  border: 1px solid var(--adm-border-dark);
  border-radius: 8px;
  cursor: pointer;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  color: var(--adm-text-regular);
  background: var(--adm-panel-strong);
  transition: color 0.18s ease, border-color 0.18s ease, background-color 0.18s ease, transform 0.18s ease;
}

.adm-pagination-btn.is-text {
  min-width: 60px;
}

.adm-pagination-btn.is-page {
  min-width: 28px;
  padding: 0 8px;
}

.adm-pagination-btn:not(:disabled):not(.is-active):hover {
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
  transform: translateY(-1px);
}

.adm-pagination-btn.is-active {
  color: #fff;
  border-color: transparent;
  background: var(--el-color-primary);
  box-shadow: 0 6px 14px rgba(64, 158, 255, 0.24);
}

.adm-pagination-btn:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.adm-pagination-ellipsis {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 20px;
  height: 28px;
  font-size: 12px;
  color: var(--adm-text-placeholder);
}

@media (max-width: 720px) {
  .adm-pagination {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
