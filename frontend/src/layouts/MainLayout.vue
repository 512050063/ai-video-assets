<template>
  <div class="adm-shell" :class="{ 'is-collapsed': collapsed }">
    <!-- 侧边栏：展开 240px，折叠 68px（参考窄栏：图标在上、文字在下） -->
    <aside class="adm-sidebar" :class="{ 'is-collapsed': collapsed }">
      <!-- 品牌区 -->
      <div class="adm-brand">
        <div class="adm-brand-logo">
          <el-icon :size="16"><VideoCamera /></el-icon>
        </div>
        <div class="adm-brand-text">
          <div class="adm-brand-name">{{ settings.siteName }}</div>
          <div class="adm-brand-sub">{{ settings.siteSubtitle }}</div>
        </div>
      </div>

      <nav class="adm-nav">
        <template v-for="group in menuGroups" :key="group.title">
          <div class="adm-nav-group">{{ group.title }}</div>
          <router-link
            v-for="m in group.items"
            :key="m.path"
            :to="m.path"
            class="adm-menu-item"
            active-class="is-active"
            :title="m.label"
            @click="closeOnMobile"
          >
            <span class="adm-menu-icon">
              <el-icon :size="16"><component :is="m.icon" /></el-icon>
            </span>
            <span class="adm-menu-text">{{ m.label }}</span>
          </router-link>
        </template>
      </nav>

    </aside>

    <!-- 主区域 -->
    <div class="adm-main">
      <!-- 顶部页头：面包屑 + 搜索 + 主题 + 账号 -->
      <header class="adm-header">
        <div class="adm-header-left">
          <button class="adm-header-icon-btn" type="button" title="折叠 / 展开菜单" @click="toggle">
            <el-icon :size="17"><component :is="collapsed ? Expand : Fold" /></el-icon>
          </button>

          <el-breadcrumb class="adm-header-crumb" separator="/">
            <el-breadcrumb-item>AI 视频创作管理台</el-breadcrumb-item>
            <el-breadcrumb-item v-if="route.meta.group">{{ route.meta.group }}</el-breadcrumb-item>
            <el-breadcrumb-item>{{ route.meta.title || '首页' }}</el-breadcrumb-item>
          </el-breadcrumb>
        </div>

        <div class="adm-header-right">
          <!-- 更新提醒：消息图标 + 待更新数量角标 -->
          <el-tooltip content="更新提醒" placement="bottom">
            <button
              class="adm-header-icon-btn adm-reminder-btn"
              type="button"
              aria-label="更新提醒"
              title="更新提醒"
              @click="reminderVisible = true"
            >
              <el-icon :size="17"><Bell /></el-icon>
              <span v-if="reminderCount > 0" class="adm-reminder-badge">{{ reminderCount }}</span>
            </button>
          </el-tooltip>

          <!-- 小图标功能区：全屏 / 主题 / 帮助 -->
          <el-tooltip :content="isFullscreen ? '退出全屏' : '全屏显示'" placement="bottom">
            <button class="adm-header-icon-btn adm-fullscreen-btn" type="button" @click="toggleFullscreen">
              <el-icon :size="17"><component :is="isFullscreen ? Aim : FullScreen" /></el-icon>
            </button>
          </el-tooltip>

          <!-- 主题切换 -->
          <el-tooltip :content="theme.isDark ? '切换到浅色主题' : '切换到深色主题'" placement="bottom">
            <button class="adm-header-icon-btn adm-theme-btn" type="button" @click="theme.toggle()">
              <el-icon :size="17"><component :is="theme.isDark ? Moon : Sunny" /></el-icon>
            </button>
          </el-tooltip>

          <el-tooltip content="使用帮助" placement="bottom">
            <button class="adm-header-icon-btn adm-help-btn" type="button" @click="helpVisible = true">
              <el-icon :size="17"><QuestionFilled /></el-icon>
            </button>
          </el-tooltip>

          <!-- 账号区：全局唯一一处 -->
          <el-dropdown trigger="click" placement="bottom-end" @command="onCommand">
            <div class="adm-user">
              <div class="adm-user-avatar">
                <img v-if="auth.user?.avatar" :src="auth.user.avatar" :alt="auth.displayName" />
                <template v-else>{{ auth.initial }}</template>
              </div>
              <div class="adm-user-text">
                <div class="adm-user-name">
                  <span class="adm-user-display">{{ auth.displayName }}</span>
                  <span v-if="auth.isAdmin" class="adm-role-tag">超管</span>
                  <span v-else-if="perm.roleName" class="adm-role-tag is-viewer">{{ perm.roleName }}</span>
                </div>
                <div class="adm-user-sub">{{ auth.user?.username }}</div>
              </div>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item command="profile">
                  <el-icon><User /></el-icon> 个人资料
                </el-dropdown-item>
                <el-dropdown-item command="password">
                  <el-icon><Lock /></el-icon> 修改密码
                </el-dropdown-item>
                <el-dropdown-item command="logout" divided>
                  <el-icon><SwitchButton /></el-icon> 退出登录
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>

      <main class="adm-content">
        <router-view v-slot="{ Component }">
          <transition name="adm-fade" mode="out-in">
            <component :is="Component" />
          </transition>
        </router-view>
      </main>
    </div>

    <!-- 个人资料：头像、昵称、联系方式统一在此维护 -->
    <el-dialog v-model="profileVisible" width="480px" :close-on-click-modal="false">
      <template #header>
        <DialogHeader :icon="User" title="个人资料" sub="维护头像与联系方式，保存后立即生效" />
      </template>
      <el-form :model="profileForm" label-width="82px">
        <el-form-item label="头像">
          <ImageUploader
            v-model:src="profileForm.avatar"
            mode="single"
            shape="circle"
            :size="72"
            tip="点击图片上传新头像，支持 jpg / png"
          />
        </el-form-item>
        <el-form-item label="用户名">
          <el-input :model-value="auth.user?.username" disabled />
        </el-form-item>
        <el-form-item label="昵称">
          <el-input v-model="profileForm.nickname" placeholder="请输入昵称" maxlength="30" />
        </el-form-item>
        <el-form-item label="手机">
          <el-input v-model="profileForm.phone" placeholder="选填" maxlength="20" />
        </el-form-item>
        <el-form-item label="邮箱">
          <el-input v-model="profileForm.email" placeholder="选填" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="profileVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveProfile">保存</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码 -->
    <el-dialog v-model="passwordVisible" width="420px" :close-on-click-modal="false">
      <template #header>
        <DialogHeader :icon="Lock" title="修改密码" sub="新密码至少 6 位，修改后需重新登录" tone="amber" />
      </template>
      <el-form :model="passwordForm" label-width="82px">
        <el-form-item label="原密码">
          <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入原密码" />
        </el-form-item>
        <el-form-item label="新密码">
          <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="至少 6 位" />
        </el-form-item>
        <el-form-item label="确认密码">
          <el-input v-model="passwordForm.confirm" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordVisible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="savePassword">确认修改</el-button>
      </template>
    </el-dialog>

    <!-- 使用帮助 -->
    <el-dialog v-model="helpVisible" width="560px">
      <template #header>
        <DialogHeader :icon="QuestionFilled" title="使用帮助" sub="三步创作流程与快捷说明" tone="lilac" />
      </template>
      <div class="help-list">
        <div class="help-step">
          <span class="help-no">1</span>
          <div>
            <div class="help-title">创意灵感</div>
            <div class="help-desc">粘贴抖音链接解析名称、话题标签与视频数据，点赞投票筛选，点状态标签推进流程；填写创作人、优先级与排期日期。</div>
          </div>
        </div>
        <div class="help-step">
          <span class="help-no">2</span>
          <div>
            <div class="help-title">视频创作</div>
            <div class="help-desc">绑定人物资产与共享素材，选择制作平台、录入提示词，系统自动记录开始时间与完成时间。</div>
          </div>
        </div>
        <div class="help-step">
          <span class="help-no">3</span>
          <div>
            <div class="help-title">发布数据</div>
            <div class="help-desc">选择发布平台与账号，回填发布链接并录入播放、点赞、评论、转发数据，可追踪增长趋势。</div>
          </div>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" @click="helpVisible = false">知道了</el-button>
      </template>
    </el-dialog>

    <!-- 更新提醒弹窗：页头消息图标点击查看 -->
    <UpdateReminderDialog
      v-model="reminderVisible"
      @count="reminderCount = $event"
    />
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Aim,
  Avatar,
  Bell,
  Collection,
  Connection,
  DataLine,
  Expand,
  Files,
  Fold,
  FullScreen,
  Lock,
  Moon,
  QuestionFilled,
  Setting,
  Sunny,
  SwitchButton,
  TrendCharts,
  User,
  VideoCamera
} from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'
import { usePermissionStore } from '../stores/permission'
import { useSettingsStore } from '../stores/settings'
import { useThemeStore } from '../stores/theme'
import { api } from '../api'
import DialogHeader from '../components/ui/DialogHeader.vue'
import ImageUploader from '../components/ui/ImageUploader.vue'
import UpdateReminderDialog from '../components/ui/UpdateReminderDialog.vue'

const auth = useAuthStore()
const perm = usePermissionStore()
const settings = useSettingsStore()
const theme = useThemeStore()
const router = useRouter()
const route = useRoute()
const collapsed = ref(false)
const saving = ref(false)
const isFullscreen = ref(false)
const helpVisible = ref(false)
const reminderVisible = ref(false)
const reminderCount = ref(0)

const profileVisible = ref(false)
const passwordVisible = ref(false)

const profileForm = reactive({ nickname: '', phone: '', email: '', avatar: '' })
const passwordForm = reactive({ old_password: '', new_password: '', confirm: '' })

// 菜单分组：概览 → 创作流程（五步）→ 资产库 → 我的（我的账号）→ 系统（仅管理员）
// 各菜单按模块角色权限过滤（见 stores/permission.js）
const menuGroups = computed(() => {
  const groups = [
    {
      title: '概览',
      items: [{ path: '/dashboard', label: '首页', icon: DataLine, key: 'dashboard' }]
    },
    {
      title: '创作流程',
      items: [
        { path: '/ideas', label: '创意灵感', icon: Collection, key: 'ideas' },
        { path: '/productions', label: '视频创作', icon: VideoCamera, key: 'productions' },
        { path: '/publish-stats', label: '发布数据', icon: TrendCharts, key: 'publish-stats' }
      ]
    },
    {
      title: '资产库',
      items: [
        { path: '/characters', label: '人物资产', icon: User, key: 'characters' },
        { path: '/materials', label: '素材共享', icon: Files, key: 'materials' }
      ]
    },
    {
      // 「我的账号」独立成组，位置在「配置中心」菜单上方
      title: '我的',
      items: [{ path: '/publish-accounts', label: '我的账号', icon: Connection, key: 'publish-accounts' }]
    }
  ]
  if (auth.isAdmin) {
    groups.push({
      title: '系统',
      items: [
        { path: '/users', label: '用户管理', icon: Avatar, key: 'users' },
        { path: '/roles', label: '角色权限', icon: Lock, key: 'roles' },
        { path: '/settings', label: '配置中心', icon: Setting, key: 'settings' }
      ]
    })
  }
  // 按模块角色过滤菜单；过滤后为空分组的整组隐藏
  return groups
    .map((g) => ({ ...g, items: g.items.filter((m) => perm.canMenu(m.key)) }))
    .filter((g) => g.items.length)
})

function toggle() {
  collapsed.value = !collapsed.value
}

function closeOnMobile() {
  if (window.innerWidth < 768) collapsed.value = true
}

// 全屏切换
async function toggleFullscreen() {
  try {
    if (!document.fullscreenElement) {
      await document.documentElement.requestFullscreen()
      isFullscreen.value = true
    } else {
      await document.exitFullscreen()
      isFullscreen.value = false
    }
  } catch (e) {
    ElMessage.warning('当前浏览器不支持全屏，或已被拒绝')
  }
}

function onFullscreenChange() {
  isFullscreen.value = !!document.fullscreenElement
}

function onCommand(cmd) {
  if (cmd === 'profile') {
    profileForm.nickname = auth.user?.nickname || ''
    profileForm.phone = auth.user?.phone || ''
    profileForm.email = auth.user?.email || ''
    profileForm.avatar = auth.user?.avatar || ''
    profileVisible.value = true
  } else if (cmd === 'password') {
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm = ''
    passwordVisible.value = true
  } else if (cmd === 'logout') {
    auth.logout()
    router.push('/login')
  }
}

async function saveProfile() {
  saving.value = true
  try {
    if (profileForm.avatar !== (auth.user?.avatar || '')) {
      await api.put('/auth/avatar', { avatar: profileForm.avatar })
    }
    await api.put('/auth/profile', {
      nickname: profileForm.nickname,
      phone: profileForm.phone,
      email: profileForm.email
    })
    await auth.fetchMe()
    profileVisible.value = false
    ElMessage.success('资料已更新')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function savePassword() {
  if (!passwordForm.old_password) {
    ElMessage.warning('请输入原密码')
    return
  }
  if (passwordForm.new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  saving.value = true
  try {
    await api.post('/auth/password', {
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password
    })
    passwordVisible.value = false
    ElMessage.success('密码已修改')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '修改失败')
  } finally {
    saving.value = false
  }
}

async function loadReminderCount() {
  try {
    const { data } = await api.get('/publish-accounts/reminders', { params: { only_due: 1 } })
    reminderCount.value = Array.isArray(data) ? data.length : 0
  } catch (e) {
    reminderCount.value = 0
  }
}

onMounted(() => {
  // 低分辨率屏幕默认收起侧栏，把宽度让给表格内容
  if (window.innerWidth < 1280) collapsed.value = true
  auth.fetchMe()
  settings.load()
  perm.load()
  loadReminderCount()
  document.addEventListener('fullscreenchange', onFullscreenChange)
})

onUnmounted(() => {
  document.removeEventListener('fullscreenchange', onFullscreenChange)
})
</script>

<style scoped>
.adm-shell {
  display: flex;
  min-height: 100vh;
  background: transparent;
  color: var(--adm-text-primary);
  --adm-sidebar-current: var(--adm-sidebar-width);
}

.adm-shell.is-collapsed {
  --adm-sidebar-current: var(--adm-sidebar-width-collapsed);
}

/* ---------- 顶部页头 ---------- */
.adm-header {
  height: var(--adm-header-height);
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 0 24px 0 16px;
  background: var(--adm-surface);
  backdrop-filter: blur(28px) saturate(150%);
  -webkit-backdrop-filter: blur(28px) saturate(150%);
  border-bottom: 1px solid var(--adm-border);
  position: sticky;
  top: 0;
  z-index: 15;
}

.adm-header-left {
  display: flex;
  align-items: center;
  gap: 14px;
  min-width: 0;
}

.adm-header-crumb {
  font-size: 13px;
  white-space: nowrap;
  padding-left: 6px;
  border-left: 1px solid var(--adm-border-dark);
}

.adm-header-right {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}

.adm-header-icon-btn {
  width: 32px;
  height: 32px;
  display: grid;
  place-items: center;
  padding: 0;
  border-radius: 10px;
  cursor: pointer;
  color: var(--adm-text-regular);
  background: transparent;
  border: 1px solid transparent;
  transition: background-color 0.18s ease, color 0.18s ease, border-color 0.18s ease;
}

.adm-header-icon-btn:hover {
  color: var(--el-color-primary);
  background: var(--adm-active-bg);
  border-color: var(--adm-border);
}

/* 更新提醒角标 */
.adm-reminder-btn {
  position: relative;
  overflow: visible;
}
/* 角标移到按钮右上角外侧，避免数字压住铃铛图标 */
.adm-reminder-badge {
  position: absolute;
  top: -4px;
  right: -5px;
  min-width: 15px;
  height: 15px;
  padding: 0 3px;
  border-radius: 999px;
  background: var(--adm-coral, #e05c4b);
  color: #fff;
  font-size: 9px;
  font-weight: 700;
  line-height: 15px;
  text-align: center;
  box-shadow: 0 0 0 2px var(--adm-surface);
  pointer-events: none;
}

/* ---------- 侧边栏 ---------- */
.adm-sidebar {
  width: var(--adm-sidebar-current);
  box-sizing: border-box;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  background: var(--adm-surface);
  backdrop-filter: blur(28px) saturate(150%);
  -webkit-backdrop-filter: blur(28px) saturate(150%);
  border-right: 1px solid var(--adm-border);
  transition: width 0.24s cubic-bezier(0.22, 1, 0.36, 1);
  position: sticky;
  top: 0;
  height: 100vh;
  overflow: hidden;
  z-index: 20;
}

/* 品牌区 */
.adm-brand {
  height: var(--adm-header-height);
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 0 16px;
  border-bottom: 1px solid var(--adm-border);
  flex-shrink: 0;
}

.adm-sidebar.is-collapsed .adm-brand {
  justify-content: center;
  padding: 0;
}

.adm-brand-logo {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 12px;
  background: var(--el-color-primary);
  color: #fff;
  display: grid;
  place-items: center;
  box-shadow: 0 4px 14px rgba(64, 158, 255, 0.35);
}

.adm-brand-text {
  line-height: 1.25;
  overflow: hidden;
}

.adm-brand-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--adm-text-primary);
  white-space: nowrap;
}

.adm-brand-sub {
  font-size: 11px;
  color: var(--adm-text-secondary);
  white-space: nowrap;
}

/* 导航 */
.adm-nav {
  flex: 1;
  overflow-y: auto;
  overflow-x: hidden;
  padding: 12px 8px;
}
.adm-nav-group {
  font-size: 12px;
  color: var(--adm-text-secondary);
  padding: 4px 12px 8px;
  white-space: nowrap;
}

/* 折叠态：分组标题整体收起，保证所有菜单项间距完全统一（参考窄栏样式） */
.adm-sidebar.is-collapsed .adm-nav-group {
  display: none;
}

/* 页头账号区：无底色标签、无下拉箭头 */
.adm-user {
  display: flex;
  align-items: center;
  gap: 8px;
  max-width: 190px;
  padding: 4px 6px;
  border-radius: 10px;
  background: transparent;
  box-shadow: none;
  overflow: hidden;
  cursor: pointer;
  transition: background-color 0.18s ease;
}

.adm-user:hover {
  background: var(--adm-active-bg);
}

.adm-user-avatar {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
  border-radius: 999px;
  background: var(--el-color-primary);
  color: #fff;
  display: grid;
  place-items: center;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  box-shadow: 0 2px 8px rgba(64, 158, 255, 0.28);
}

.adm-user-avatar img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.adm-user-text {
  line-height: 1.35;
  overflow: hidden;
  min-width: 0;
}

.adm-user-name {
  font-size: 13px;
  color: var(--adm-text-primary);
  display: flex;
  align-items: center;
  gap: 5px;
  white-space: nowrap;
  min-width: 0;
}
.adm-user-display {
  max-width: 84px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.adm-user-sub {
  font-size: 11px;
  color: var(--adm-text-secondary);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  max-width: 130px;
}

.adm-role-tag {
  display: inline-flex;
  align-items: center;
  height: 16px;
  padding: 0 5px;
  border-radius: 999px;
  font-size: 10px;
  font-weight: 600;
  color: #b88230;
  background: #fdf6ec;
  border: 1px solid #f0d9a8;
}

.adm-role-tag.is-viewer {
  color: #5a7086;
  background: rgba(123, 163, 209, 0.14);
  border-color: rgba(123, 163, 209, 0.34);
}

/* ---------- 主区域 ---------- */
.adm-main {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

/* 内容区：占满可用宽度，不设固定最大宽 */
.adm-content {
  flex: 1;
  width: 100%;
  min-width: 0;
  padding: 20px 24px 28px;
  box-sizing: border-box;
}

/* 路由转场：克制淡入 */
.adm-fade-enter-active,
.adm-fade-leave-active {
  transition: opacity 0.18s ease;
}

.adm-fade-enter-from,
.adm-fade-leave-to {
  opacity: 0;
}

/* ---------- 帮助弹窗 ---------- */
.help-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.help-step {
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

.help-no {
  width: 24px;
  height: 24px;
  flex-shrink: 0;
  display: grid;
  place-items: center;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  color: var(--el-color-primary);
  background: var(--adm-active-bg);
  border: 1px solid var(--adm-border-dark);
}

.help-title {
  font-size: 13.5px;
  font-weight: 700;
  color: var(--adm-text-primary);
}

.help-desc {
  margin-top: 2px;
  font-size: 12.5px;
  line-height: 1.6;
  color: var(--adm-text-secondary);
}

/* 低分辨率适配 */
@media (max-width: 1366px) {
  .adm-header {
    padding: 0 16px 0 10px;
    gap: 8px;
  }
  .adm-header-left { gap: 8px; }
  .adm-header-right { gap: 4px; }
  .adm-user-sub { display: none; }
  .adm-content { padding: 14px 16px 20px; }
}

@media (max-width: 1100px) {
  .adm-header-crumb :deep(.el-breadcrumb__item:first-child) { display: none; }
  .adm-help-btn { display: none; }
}

@media (max-width: 768px) {
  .adm-content {
    padding: 12px;
  }
  .adm-user-text { display: none; }
}
</style>
