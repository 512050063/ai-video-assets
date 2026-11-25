<template>
  <el-dialog
    v-model="visible"
    width="640px"
    align-center
    class="adm-dialog-detail reminder-dialog"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <template #header>
      <DialogHeader
        :icon="Bell"
        title="更新提醒"
        sub="离线账号提示重新扫码；在线账号按更新节奏提醒排期"
        tone="coral"
      />
    </template>

    <div v-loading="loading" class="reminder-list">
      <div
        v-for="item in items"
        :key="item.account_id"
        class="reminder-item"
        :class="{ 'is-due': item.is_due, 'is-offline': item.is_offline }"
      >
        <div class="reminder-avatar">
          <img v-if="item.avatar" :src="item.avatar" :alt="item.account_name" />
          <img v-else src="/placeholder.svg" class="is-empty" alt="暂无头像" />
        </div>
        <div class="reminder-main">
          <div class="reminder-title">
            {{ item.account_name }}
            <span class="reminder-platform">{{ item.platform || '未标注' }}</span>
          </div>
          <div class="reminder-meta">
            <span v-if="item.is_offline" class="reminder-chip is-offline">离线</span>
            <span v-else class="reminder-chip">{{ item.update_rhythm || '日更' }}</span>
            <span v-if="item.responsible_name" class="reminder-owner">责任人：{{ item.responsible_name }}</span>
            <span v-else class="reminder-owner">未指定责任人</span>
          </div>
          <div class="reminder-reason">{{ item.reason }}</div>
        </div>
        <div class="reminder-action">
          <el-button
            :type="item.is_offline ? 'danger' : 'primary'"
            size="small"
            :loading="schedulingId === item.account_id"
            @click="handleAction(item)"
          >{{ item.action_label || '去排期' }}</el-button>
        </div>
      </div>

      <div v-if="!loading && !items.length" class="reminder-empty">
        <el-icon :size="28"><CircleCheckFilled /></el-icon>
        <span>暂无提醒，账号均在线且在正常更新节奏内</span>
      </div>
    </div>

    <template #footer>
      <el-button @click="visible = false">关闭</el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, CircleCheckFilled } from '@element-plus/icons-vue'
import DialogHeader from './DialogHeader.vue'
import { api } from '../../api'

const props = defineProps({
  modelValue: { type: Boolean, default: false },
  onlyDue: { type: Boolean, default: true }
})
const emit = defineEmits(['update:modelValue', 'count', 'scheduled'])
const router = useRouter()

const visible = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v)
})

const loading = ref(false)
const items = ref([])
const schedulingId = ref(null)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/publish-accounts/reminders', {
      params: { only_due: props.onlyDue ? 1 : 0 }
    })
    items.value = Array.isArray(data) ? data : []
    emit('count', items.value.length)
  } catch (e) {
    items.value = []
  } finally {
    loading.value = false
  }
}

function handleAction(item) {
  if (item.is_offline || item.kind === 'offline') {
    visible.value = false
    router.push('/publish-accounts')
    return
  }
  return schedule(item)
}

async function schedule(item) {
  schedulingId.value = item.account_id
  try {
    const { data } = await api.post(`/publish-accounts/${item.account_id}/schedule`)
    ElMessage.success(`已加入创意灵感「${data.title || ''}」`)
    emit('scheduled', data)
    await load()
    router.push('/ideas')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '排期失败，请重试')
  } finally {
    schedulingId.value = null
  }
}

watch(
  () => props.modelValue,
  (v) => { if (v) load() }
)
</script>

<style scoped>
.reminder-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 52vh;
  min-height: 120px;
  overflow-y: auto;
  padding-right: 4px;
}
.reminder-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--adm-border);
  border-radius: 12px;
  background: var(--adm-panel-soft);
}
.reminder-item.is-due {
  border-color: rgba(230, 162, 60, 0.4);
  background: var(--adm-state-warning-bg);
}
.reminder-item.is-offline {
  border-color: rgba(224, 92, 75, 0.4);
  background: var(--adm-state-danger-bg, rgba(224, 92, 75, 0.08));
}
.reminder-avatar {
  width: 42px;
  height: 42px;
  flex-shrink: 0;
  border-radius: 12px;
  overflow: hidden;
  background: var(--adm-surface-sunken);
}
.reminder-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.reminder-avatar img.is-empty {
  object-fit: contain;
  padding: 4px;
  opacity: 0.55;
}
.reminder-main {
  min-width: 0;
  flex: 1;
}
.reminder-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--adm-text-primary);
  display: flex;
  align-items: center;
  gap: 8px;
}
.reminder-platform {
  font-size: 11px;
  font-weight: 400;
  color: var(--adm-text-secondary);
}
.reminder-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--adm-text-secondary);
}
.reminder-chip {
  display: inline-flex;
  align-items: center;
  height: 18px;
  padding: 0 7px;
  border-radius: 999px;
  font-weight: 600;
  color: var(--adm-blue, #2f6fb5);
  background: var(--adm-blue-bg, #dcecff);
}
.reminder-chip.is-offline {
  color: var(--el-color-danger);
  background: var(--adm-state-danger-bg, rgba(224, 92, 75, 0.1));
}
.reminder-reason {
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--adm-state-warning-fg, #b88230);
}
.reminder-item.is-offline .reminder-reason {
  color: var(--el-color-danger);
}
.reminder-action {
  flex-shrink: 0;
}
.reminder-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 36px 0;
  color: var(--adm-text-placeholder);
  font-size: 13px;
}
</style>
