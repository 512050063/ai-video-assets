<template>
  <div class="stack">
    <PageHeader :icon="Avatar" title="用户管理" tone="lilac" desc="管理系统的账号、角色与数据权限">
      <template #extra>
        <el-button type="primary" :icon="Plus" @click="openCreate">新建用户</el-button>
      </template>
    </PageHeader>

    <!-- 概览：与创作流程共用 StatCard -->
    <div class="stat-row">
      <StatCard
        v-for="s in summary"
        :key="s.label"
        :label="s.label"
        :value="s.value"
        :icon="s.icon"
        :tone="s.tone"
      />
    </div>

    <el-card shadow="never" class="adm-card adm-card--table" :class="{ 'is-loading': loading }">
      <GridSkeleton v-if="loading" :rows="8" :cols="6" />
      <div class="adm-table-wrap">
      <el-table :data="pagedList" stripe style="width: 100%" empty-text="还没有用户">
        <el-table-column label="账号" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <div class="user-cell">
              <div class="user-avatar">
                <img v-if="row.avatar" :src="row.avatar" :alt="row.nickname" />
                <template v-else>{{ (row.nickname || row.username).slice(0, 1).toUpperCase() }}</template>
              </div>
              <div class="user-cell-text">
                <span class="adm-cell-text adm-cell-text--clamp2" :title="row.nickname || row.username">{{ row.nickname || row.username }}</span>
                <span class="adm-cell-sub" :title="row.username">@{{ row.username }}</span>
              </div>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="角色权限" width="120" align="center">
          <template #default="{ row }">
            <el-tooltip :content="moduleRoleDesc(row.module_role)" placement="top">
              <el-tag :type="moduleRoleType(row.module_role)" effect="light">
                {{ moduleRoleLabel(row.module_role) }}
              </el-tag>
            </el-tooltip>
          </template>
        </el-table-column>

        <el-table-column label="功能限制" min-width="180">
          <template #default="{ row }">
            <div class="adm-cell-tags">
              <span v-if="row.module_role === 'super'" class="adm-tag-chip">全部功能 · 全部数据</span>
              <template v-else>
                <span class="adm-tag-chip">{{ row.can_create ? '可创建' : '只读' }}</span>
                <span class="adm-tag-chip">{{ row.can_view_all ? '可见全部' : '仅看自己' }}</span>
                <span class="adm-tag-chip" :title="roleButtonSummary(row.module_role)">
                  功能 {{ roleButtonCount(row.module_role) }} 项
                </span>
              </template>
            </div>
          </template>
        </el-table-column>

        <el-table-column label="制作" width="110" align="right">
          <template #default="{ row }">
            <span class="adm-cell-num user-assets">{{ row.production_count }} 条制作</span>
          </template>
        </el-table-column>

        <el-table-column label="状态" width="88" align="center">
          <template #default="{ row }">
            <el-switch
              :model-value="row.is_active"
              :disabled="row.id === auth.user?.id"
              @change="(v) => toggleActive(row, v)"
            />
          </template>
        </el-table-column>

        <el-table-column label="最近登录" width="152" align="right">
          <template #default="{ row }">
            <span class="adm-cell-time" :title="row.last_login_at ? formatDateTime(row.last_login_at) : '从未登录'">{{ row.last_login_at ? formatDateTime(row.last_login_at) : '从未登录' }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="150" fixed="right" align="center">
          <template #default="{ row }">
            <div class="adm-cell-actions">
              <el-button type="text" size="small" @click="openEdit(row)">编辑</el-button>
              <el-button type="text" size="small" @click="openReset(row)">重置</el-button>
              <el-button type="text" size="small" class="danger-text" :disabled="row.id === auth.user?.id" @click="remove(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
        <template #empty>
          <el-empty :image-size="100" description="还没有用户" />
        </template>
      </el-table>
      </div>

      <AppPagination v-model:page="page" :total="list.length" v-model:page-size="PAGE_SIZE" />
    </el-card>

    <!-- 新建 / 编辑 -->
    <el-dialog v-model="dialog.visible" width="480px">
      <template #header>
        <DialogHeader :icon="Avatar" :title="dialog.isEdit ? '编辑用户' : '新建用户'" sub="角色权限统一决定可见菜单与可用功能，保存后立即生效" tone="lilac" />
      </template>
      <el-form :model="dialog.form" label-width="88px">
        <el-form-item label="用户名">
          <el-input v-model="dialog.form.username" :disabled="dialog.isEdit" placeholder="登录名，至少 3 位" />
        </el-form-item>
        <el-form-item v-if="!dialog.isEdit" label="初始密码">
          <el-input v-model="dialog.form.password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="dialog.form.nickname" placeholder="显示名称" maxlength="30" />
        </el-form-item>
        <el-form-item label="角色权限">
          <el-select v-model="dialog.form.module_role" style="width: 100%" @change="onRoleChange">
            <el-option
              v-for="r in MODULE_ROLES"
              :key="r.value"
              :label="`${r.label} · ${r.desc}`"
              :value="r.value"
            />
          </el-select>
          <div class="role-perm-summary">
            <div class="role-perm-line">
              可见菜单 <b>{{ selectedRolePerm.menus }}</b> 项 · 可用功能 <b>{{ selectedRolePerm.buttons }}</b> 项
            </div>
            <div class="role-perm-line">{{ selectedRolePerm.desc }}</div>
            <div class="role-perm-line">功能限制由「角色权限」页统一配置，无需单独设置创建权限与数据范围</div>
          </div>
        </el-form-item>
        <el-form-item label="联系方式">
          <div class="contact-row">
            <el-input v-model="dialog.form.phone" placeholder="手机号" />
            <el-input v-model="dialog.form.email" placeholder="邮箱" />
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="resetVisible" width="380px">
      <template #header>
        <DialogHeader :icon="Lock" title="重置密码" sub="为指定账号设置新的登录密码" tone="amber" />
      </template>
      <el-form label-width="80px">
        <el-form-item label="账号">
          <el-input :model-value="resetTarget.nickname || resetTarget.username" disabled />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="resetPassword" placeholder="至少 6 位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="doReset">确认重置</el-button>
      </template>
    </el-dialog>

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="confirm.visible"
      title="删除用户"
      :message="confirm.message"
      :loading="confirm.loading"
      @confirm="doRemove"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Avatar, CircleCheck, Lock, Plus, User, UserFilled, WarningFilled } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import AppPagination from '../components/ui/AppPagination.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import StatCard from '../components/ui/StatCard.vue'
import { api, formatDateTime } from '../api'
import { MODULE_ROLES, moduleRoleLabel, moduleRoleType } from '../api/platforms'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const list = ref([])
const saving = ref(false)
const page = ref(1)

const PAGE_SIZE = ref(12)

// 客户端分页
const pagedList = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE.value
  return list.value.slice(start, start + PAGE_SIZE.value)
})

// 角色权限矩阵：菜单与功能按钮均由「角色权限」页统一配置
const roleMatrix = ref([])

function roleConfig(key) {
  return roleMatrix.value.find((r) => r.key === key) || null
}
function roleButtonCount(key) {
  if (key === 'super') return '全部'
  return roleConfig(key)?.buttons?.length ?? 0
}
function roleButtonSummary(key) {
  const cfg = roleConfig(key)
  if (!cfg) return ''
  return `可见菜单：${cfg.menus.join('、') || '无'}；可用功能：${cfg.buttons.join('、') || '无'}`
}

// 角色权限（唯一权限控制入口：决定可见菜单、可用按钮与功能限制）
function moduleRoleDesc(key) {
  const found = MODULE_ROLES.find((r) => r.value === key)
  return roleConfig(key)?.desc || found?.desc || '默认创作角色'
}

// 新建 / 编辑弹窗里展示当前角色权限的实际限制
const selectedRolePerm = computed(() => {
  const key = dialog.form.module_role
  const cfg = roleConfig(key)
  const builtin = MODULE_ROLES.find((r) => r.value === key)
  return {
    desc: cfg?.desc || builtin?.desc || '',
    menus: cfg?.menus?.length ?? 0,
    buttons: cfg?.buttons?.length ?? 0
  }
})

const summary = computed(() => [
  { label: '账号总数', value: list.value.length, icon: UserFilled, tone: 'lilac' },
  { label: '超管', value: list.value.filter((u) => u.role === 'admin').length, icon: User, tone: 'coral' },
  { label: '已停用', value: list.value.filter((u) => !u.is_active).length, icon: WarningFilled, tone: 'amber' },
  {
    label: '本月活跃',
    value: list.value.filter((u) => {
      if (!u.last_login_at) return false
      const d = new Date(u.last_login_at)
      const now = new Date()
      return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth()
    }).length,
    icon: CircleCheck,
    tone: 'mint'
  }
])

const dialog = reactive({
  visible: false,
  isEdit: false,
  id: null,
  saving: false,
  form: {
    username: '',
    password: '',
    nickname: '',
    role: 'creator',
    can_create: true,
    can_view_all: true,
    module_role: 'production',
    phone: '',
    email: ''
  }
})

const resetVisible = ref(false)
const resetTarget = ref({})
const resetPassword = ref('')
const confirm = reactive({ visible: false, loading: false, message: '', id: null })

// 角色权限是唯一控制入口：菜单 / 按钮由后端角色矩阵决定，旧字段仅同步兼容值
function onRoleChange(roleKey) {
  const isSuper = roleKey === 'super'
  dialog.form.role = isSuper ? 'admin' : 'creator'
  dialog.form.can_create = true
  dialog.form.can_view_all = true
}

function openCreate() {
  dialog.isEdit = false
  dialog.id = null
  Object.assign(dialog.form, {
    username: '',
    password: '',
    nickname: '',
    role: 'creator',
    can_create: true,
    can_view_all: true,
    module_role: 'production',
    phone: '',
    email: ''
  })
  dialog.visible = true
}

function openEdit(row) {
  dialog.isEdit = true
  dialog.id = row.id
  Object.assign(dialog.form, {
    username: row.username,
    password: '',
    nickname: row.nickname || '',
    role: row.role || 'creator',
    can_create: row.can_create,
    can_view_all: row.can_view_all,
    module_role: row.module_role || 'production',
    phone: row.phone || '',
    email: row.email || ''
  })
  onRoleChange(dialog.form.module_role)
  dialog.visible = true
}

function openReset(row) {
  resetTarget.value = row
  resetPassword.value = ''
  resetVisible.value = true
}

async function load() {
  try {
    const { data } = await api.get('/users')
    list.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载用户列表失败')
  }
  try {
    const { data } = await api.get('/roles')
    roleMatrix.value = Array.isArray(data) ? data : []
  } catch {
    roleMatrix.value = []
  }
}

async function save() {
  const f = dialog.form
  if (!dialog.isEdit) {
    if (!f.username || f.username.length < 3) {
      ElMessage.warning('用户名至少 3 个字符')
      return
    }
    if (!f.password || f.password.length < 6) {
      ElMessage.warning('初始密码至少 6 位')
      return
    }
  }
  dialog.saving = true
  try {
    if (dialog.isEdit) {
      await api.put(`/users/${dialog.id}`, {
        nickname: f.nickname,
        module_role: f.module_role,
        phone: f.phone,
        email: f.email
      })
    } else {
      await api.post('/users', {
        username: f.username,
        password: f.password,
        nickname: f.nickname,
        module_role: f.module_role,
        phone: f.phone,
        email: f.email
      })
    }
    dialog.visible = false
    ElMessage.success('保存成功')
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    dialog.saving = false
  }
}

async function toggleActive(row, value) {
  try {
    await api.put(`/users/${row.id}`, { is_active: value })
    row.is_active = value
    ElMessage.success(value ? '账号已启用' : '账号已停用')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
    load()
  }
}

async function doReset() {
  if (!resetPassword.value || resetPassword.value.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  saving.value = true
  try {
    await api.post(`/users/${resetTarget.value.id}/reset-password`, { new_password: resetPassword.value })
    resetVisible.value = false
    ElMessage.success('密码已重置')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  } finally {
    saving.value = false
  }
}

function remove(row) {
  confirm.message = `确定删除账号「${row.nickname || row.username}」吗？该操作不可撤销，其创建的数据将保留。`
  confirm.id = row.id
  confirm.visible = true
}

async function doRemove() {
  confirm.loading = true
  try {
    await api.delete(`/users/${confirm.id}`)
    ElMessage.success('已删除')
    confirm.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    confirm.loading = false
  }
}

onMounted(load)
</script>

<style scoped>
/* 账号复合单元格：头像 + 名称/用户名两行，沿用公共 adm-cell-text / adm-cell-sub */
.user-cell {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}
.user-avatar {
  width: 34px;
  height: 34px;
  flex-shrink: 0;
  border-radius: 11px;
  background: var(--el-color-primary);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
}
.user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}
.user-cell-text {
  min-width: 0;
  line-height: 1.3;
}
.user-assets {
  font-size: 12.5px;
  color: var(--adm-text-secondary);
}
.contact-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
  width: 100%;
}
.role-perm-summary {
  width: 100%;
  margin-top: 6px;
  padding: 8px 10px;
  border-radius: 8px;
  background: var(--adm-active-bg);
  color: var(--adm-text-secondary);
  font-size: 12px;
  line-height: 1.6;
}
.role-perm-line b {
  color: var(--el-color-primary);
  font-weight: 600;
}
</style>
