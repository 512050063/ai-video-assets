<template>
  <header class="page-head">
    <div class="page-head-main">
      <span class="page-head-icon" :class="`is-${tone}`">
        <el-icon :size="18"><component :is="icon" /></el-icon>
      </span>
      <div class="page-head-text">
        <h2 class="adm-page-title">{{ title }}</h2>
        <p v-if="desc" class="adm-page-desc">{{ desc }}</p>
      </div>
    </div>

    <div class="page-head-right">
      <slot name="extra" />
    </div>
  </header>
</template>

<script setup>
defineProps({
  /** 标题左侧的图标组件 */
  icon: { type: [Object, Function], required: true },
  title: { type: String, required: true },
  desc: { type: String, default: '' },
  /** 图标底色基调 */
  tone: { type: String, default: 'primary' }
})
</script>

<style scoped>
/* 内容区头部：无背景横幅，仅保留左右对齐与一条轻分隔线 */
.page-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  min-height: 58px;
  margin-bottom: 16px;
  padding: 0 2px 12px;
  box-sizing: border-box;
  border-bottom: 1px solid var(--adm-border-dark);
  flex-wrap: wrap;
}

.page-head-main {
  display: flex;
  align-items: center;
  gap: 11px;
  min-width: 0;
}

/* 图标徽章：与标题同一水平线 */
.page-head-icon {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 11px;
  display: grid;
  place-items: center;
  color: var(--adm-blue);
  background: var(--adm-blue-bg);
}

.page-head-icon.is-primary {
  color: var(--el-color-primary);
  background: var(--adm-active-bg);
}

.page-head-icon.is-coral {
  color: var(--adm-coral);
  background: var(--adm-coral-bg);
}

.page-head-icon.is-mint {
  color: var(--adm-mint);
  background: var(--adm-mint-bg);
}

.page-head-icon.is-amber {
  color: var(--adm-amber);
  background: var(--adm-amber-bg);
}

.page-head-icon.is-lilac {
  color: var(--adm-lilac);
  background: var(--adm-lilac-bg);
}

.page-head-text {
  min-width: 0;
}

.page-head-text .adm-page-title {
  font-size: 20px;
  line-height: 1.3;
}

.page-head-text .adm-page-desc {
  margin-top: 3px;
  font-size: 12.5px;
  line-height: 1.4;
  color: var(--adm-text-secondary);
}

.page-head-right {
  margin-left: auto;
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 1366px) {
  .page-head {
    min-height: 52px;
    padding-bottom: 10px;
    gap: 10px;
  }
  .page-head-text .adm-page-title { font-size: 18px; }
  .page-head-text .adm-page-desc { font-size: 11.5px; }
  .page-head-right { gap: 6px; }
}

@media (max-width: 768px) {
  .page-head {
    min-height: auto;
    padding-bottom: 10px;
  }
}
</style>
