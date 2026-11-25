<template>
  <component
    :is="clickable ? 'button' : 'div'"
    class="adm-stat"
    :class="[`is-${tone}`, { 'is-active': active, 'is-clickable': clickable }]"
    :type="clickable ? 'button' : undefined"
    @click="clickable && $emit('click')"
  >
    <span class="adm-stat-icon">
      <el-icon :size="20"><component :is="icon" /></el-icon>
    </span>

    <span class="adm-stat-body">
      <span class="adm-stat-label">{{ label }}</span>
      <span class="adm-stat-metric">
        <span class="adm-stat-value adm-num">{{ value }}</span>
        <span v-if="subLabel" class="adm-stat-sub">{{ subLabel }}</span>
      </span>
    </span>
  </component>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: 0 },
  subLabel: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  tone: { type: String, default: 'blue' },
  active: { type: Boolean, default: false },
  clickable: { type: Boolean, default: false }
})

defineEmits(['click'])
</script>

<style scoped>
.adm-stat {
  display: flex;
  align-items: center;
  gap: 12px;
  min-height: 76px;
  box-sizing: border-box;
  width: 100%;
  padding: 13px 16px;
  text-align: left;
  border: 1px solid var(--adm-border-dark);
  border-radius: var(--adm-radius-md);
  background: var(--adm-panel);
  color: inherit;
  transition: transform 0.2s ease, box-shadow 0.2s ease, border-color 0.2s ease, background-color 0.2s ease;
}

.adm-stat.is-clickable {
  cursor: pointer;
  appearance: none;
  font-family: inherit;
}

.adm-stat.is-clickable:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 22px rgba(123, 163, 209, 0.18);
  border-color: var(--adm-border-deep);
}

.adm-stat.is-active {
  border-color: var(--el-color-primary);
  background: var(--adm-active-bg);
  box-shadow: 0 6px 18px rgba(64, 158, 255, 0.18);
}

/* 图标底座 */
.adm-stat-icon {
  width: 40px;
  height: 40px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 12px;
  color: var(--adm-blue);
  background: var(--adm-blue-bg);
}

.adm-stat.is-coral .adm-stat-icon { color: var(--adm-coral); background: var(--adm-coral-bg); }
.adm-stat.is-mint .adm-stat-icon { color: var(--adm-mint); background: var(--adm-mint-bg); }
.adm-stat.is-amber .adm-stat-icon { color: var(--adm-amber); background: var(--adm-amber-bg); }
.adm-stat.is-lilac .adm-stat-icon { color: var(--adm-lilac); background: var(--adm-lilac-bg); }
.adm-stat.is-primary .adm-stat-icon { color: var(--el-color-primary); background: var(--adm-active-bg); }

/* 内容 */
.adm-stat-body {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
  flex: 1;
}

.adm-stat-label {
  font-size: 12px;
  font-weight: 600;
  line-height: 1.3;
  color: var(--adm-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.adm-stat-metric {
  display: flex;
  align-items: baseline;
  gap: 6px;
  min-width: 0;
}

.adm-stat-value {
  font-size: 23px;
  font-weight: 800;
  line-height: 1.15;
  color: var(--adm-text-primary);
}

.adm-stat-sub {
  font-size: 11px;
  font-weight: 500;
  line-height: 1.4;
  color: var(--adm-text-placeholder);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
</style>
