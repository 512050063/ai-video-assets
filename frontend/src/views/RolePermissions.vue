<template>
  <div class="stack">
    <PageHeader
      :icon="Lock"
      title="角色权限"
      tone="lilac"
      desc="模块角色分工：超管 / 灵感 / 创作 / 运营，各自可见菜单与可用按钮不同"
    >
      <template #extra>
        <el-button type="primary" :icon="Check" :loading="saving" @click="saveAll">保存权限</el-button>
      </template>
    </PageHeader>

    <!-- 角色概览 -->
    <div class="stat-row">
      <StatCard
        v-for="r in roles"
        :key="r.key"
        :label="r.name"
        :value="r.menus.length"
        :icon="roleIcon(r.key)"
        :tone="roleTone(r.key)"
      />
    </div>

    <el-card shadow="never" class="adm-card adm-card--table" :class="{ 'is-loading': loading }">
      <GridSkeleton v-if="loading" :rows="8" :cols="6" />
      <div class="adm-table-wrap">
        <el-table :data="roles" stripe style="width: 100%" empty-text="暂无角色定义">
          <el-table-column label="角色" width="140" align="left">
            <template #default="{ row }">
              <div class="role-cell">
                <span class="role-name">{{ row.name }}</span>
                <span class="role-key">{{ row.key }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="职责说明" min-width="230" align="left">
            <template #default="{ row }">
              <span class="adm-cell-text adm-cell-text--clamp2" :title="row.desc">{{ row.desc }}</span>
            </template>
          </el-table-column>

          <el-table-column label="可见菜单" min-width="260" align="left">
            <template #default="{ row }">
              <div class="adm-cell-tags">
                <span
                  v-for="m in menuChips(row)"
                  :key="m.key"
                  class="adm-tag-chip"
                  :class="{ 'is-off': !row.menus.includes(m.key) }"
                  :title="m.group"
                >{{ m.title }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="可用按钮" min-width="200" align="right">
            <template #default="{ row }">
              <span class="adm-cell-num">{{ row.buttons.length }} 项</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" width="120" fixed="right" align="center">
            <template #default="{ row }">
              <div class="adm-cell-actions">
                <el-button type="text" size="small" @click="openEdit(row)">配置</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :image-size="100" description="暂无角色定义" />
          </template>
        </el-table>
      </div>
    </el-card>

    <!-- 权限配置弹窗 -->
    <el-dialog v-model="dialog.visible" width="760px" :close-on-click-modal="false">
      <template #header>
        <DialogHeader
          :icon="Lock"
          :title="`配置角色 · ${dialog.role?.name || ''}`"
          sub="勾选该角色可见的菜单与可用的按钮"
          tone="lilac"
        />
      </template>

      <div class="perm-body">
        <section class="perm-section">
          <h4 class="perm-title">可见菜单</h4>
          <div class="perm-grid">
            <el-checkbox
              v-for="m in catalog.menus"
              :key="m.key"
              :model-value="draft.menus.includes(m.key)"
              :disabled="dialog.role?.key === 'super'"
              @change="(v) => toggle(draft.menus, m.key, v)"
            >
              {{ m.title }}
              <span class="perm-sub">{{ m.group }}</span>
            </el-checkbox>
          </div>
          <div v-if="dialog.role?.key === 'super'" class="form-tip">
            超管角色恒为全量权限，菜单与按钮不可裁剪，避免把系统锁死。
          </div>
        </section>

        <el-divider />

        <section class="perm-section">
          <h4 class="perm-title">可用按钮</h4>
          <div v-for="mod in buttonModules" :key="mod.module" class="perm-module">
            <div class="perm-module-head">
              <span class="perm-module-title">{{ moduleTitle(mod.module) }}</span>
              <el-checkbox
                :model-value="isModuleAll(mod.module)"
                :indeterminate="isModulePartial(mod.module)"
                :disabled="dialog.role?.key === 'super'"
                @change="(v) => toggleModule(mod.module, v)"
              >全选</el-checkbox>
            </div>
            <div class="perm-grid">
              <el-checkbox
                v-for="b in mod.buttons"
                :key="b.key"
                :model-value="draft.buttons.includes(b.key)"
                :disabled="dialog.role?.key === 'super'"
                @change="(v) => toggle(draft.buttons, b.key, v)"
              >{{ b.label }}</el-checkbox>
            </div>
          </div>
        </section>
      </div>

      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Compass, Connection, Lock, MagicStick, Setting, User } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import StatCard from '../components/ui/StatCard.vue'
import { api } from '../api'
import { usePermissionStore } from '../stores/permission'

const perm = usePermissionStore()

const loading = ref(false)
const saving = ref(false)
const roles = ref([])
const catalog = ref({ menus: [], buttons: [] })
const dialog = reactive({ visible: false, saving: false, role: null })
const draft = reactive({ menus: [], buttons: [] })

const ROLE_ICONS = { super: Setting, inspiration: MagicStick, production: User, operation: Connection }
const ROLE_TONES = { super: 'coral', inspiration: 'amber', production: 'lilac', operation: 'mint' }

function roleIcon(key) { return ROLE_ICONS[key] || Compass }
function roleTone(key) { return ROLE_TONES[key] || 'blue' }

// 按钮按模块分组
const buttonModules = computed(() => {
  const map = {}
  ;(catalog.value.buttons || []).forEach((b) => {
    if (!map[b.module]) map[b.module] = { module: b.module, buttons: [] }
    map[b.module].buttons.push(b)
  })
  return Object.values(map)
})

function moduleTitle(module) {
  const found = (catalog.value.menus || []).find((m) => m.key === module)
  return found ? found.title : module
}

function menuChips(row) {
  return (catalog.value.menus || []).map((m) => ({
    key: m.key,
    title: m.title,
    group: m.group
  }))
}

function isModuleAll(module) {
  const list = (catalog.value.buttons || []).filter((b) => b.module === module)
  return list.length > 0 && list.every((b) => draft.buttons.includes(b.key))
}

function isModulePartial(module) {
  const list = (catalog.value.buttons || []).filter((b) => b.module === module)
  const on = list.filter((b) => draft.buttons.includes(b.key)).length
  return on > 0 && on < list.length
}

function toggle(arr, key, checked) {
  const idx = arr.indexOf(key)
  if (checked && idx < 0) arr.push(key)
  if (!checked && idx >= 0) arr.splice(idx, 1)
}

function toggleModule(module, checked) {
  const list = (catalog.value.buttons || []).filter((b) => b.module === module)
  list.forEach((b) => toggle(draft.buttons, b.key, checked))
}

async function load() {
  loading.value = true
  try {
    const [roleRes, catalogRes] = await Promise.all([
      api.get('/roles'),
      api.get('/roles/catalog')
    ])
    roles.value = roleRes.data || []
    catalog.value = catalogRes.data || { menus: [], buttons: [] }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载角色权限失败')
  } finally {
    loading.value = false
  }
}

function openEdit(row) {
  dialog.role = { ...row }
  draft.menus = [...(row.menus || [])]
  draft.buttons = [...(row.buttons || [])]
  dialog.visible = true
}

async function save() {
  if (!dialog.role) return
  dialog.saving = true
  try {
    await api.put(`/roles/${dialog.role.key}`, {
      menus: [...draft.menus],
      buttons: [...draft.buttons]
    })
    ElMessage.success('权限已保存')
    dialog.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    dialog.saving = false
  }
}

async function saveAll() {
  saving.value = true
  try {
    for (const r of roles.value) {
      if (r.key === 'super') continue
      await api.put(`/roles/${r.key}`, { menus: r.menus, buttons: r.buttons })
    }
    ElMessage.success('全部角色权限已保存')
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(load)
</script>

<style scoped>
.role-cell { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.role-name { font-size: 13.5px; font-weight: 600; color: var(--adm-text-primary); }
.role-key { font-size: 11px; color: var(--adm-text-placeholder); font-family: ui-monospace, monospace; }
.adm-tag-chip.is-off { opacity: 0.4; }

.perm-body { max-height: 62vh; overflow-y: auto; padding-right: 4px; }
.perm-section { margin-bottom: 6px; }
.perm-title { font-size: 13px; font-weight: 700; color: var(--adm-text-primary); margin: 0 0 10px; }
.perm-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 4px 12px; }
.perm-sub { font-size: 11px; color: var(--adm-text-placeholder); margin-left: 4px; }

.perm-module { margin-bottom: 14px; }
.perm-module-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 4px; }
.perm-module-title { font-size: 12.5px; font-weight: 600; color: var(--adm-text-secondary); }
</style>
