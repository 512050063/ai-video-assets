<template>
  <div class="adm-dialog-head">
    <div v-if="icon" :class="['adm-dialog-head-icon', tone ? `is-${tone}` : '']">
      <el-icon><component :is="icon" /></el-icon>
    </div>
    <div class="adm-dialog-head-text">
      <h3 class="adm-dialog-head-title">{{ title }}</h3>
      <p v-if="sub" class="adm-dialog-head-sub">{{ sub }}</p>
    </div>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  sub: { type: String, default: '' },
  icon: { type: [Object, Function], default: null },
  tone: { type: String, default: '' }
})
</script>
