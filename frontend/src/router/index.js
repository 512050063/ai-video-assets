import { createRouter, createWebHistory } from 'vue-router'
import { readToken, readUser } from '../utils/session'
import { usePermissionStore } from '../stores/permission'

// 路由 name → 后端权限矩阵的菜单 key。
// 注意：to.name 是组件名（如 IdeaLibrary），不是菜单 key，必须显式映射，否则守卫形同虚设。
export const ROUTE_MENU_KEYS = [
  'dashboard', 'ideas', 'productions',
  'publish-stats', 'publish-accounts', 'characters', 'materials', 'users', 'settings', 'roles'
]
const ROUTE_NAME_TO_MENU = {
  Dashboard: 'dashboard',
  IdeaLibrary: 'ideas',
  ProductionList: 'productions',
  ProductionCreate: 'productions',
  ProductionEditPage: 'productions',
  PublishStats: 'publish-stats',
  PublishAccounts: 'publish-accounts',
  CharacterLibrary: 'characters',
  MaterialSharing: 'materials',
  UserManagement: 'users',
  SystemSettings: 'settings',
  roles: 'roles'
}

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/Login.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layouts/MainLayout.vue'),
    redirect: '/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('../views/Dashboard.vue'),
        meta: { title: '首页', group: '概览' }
      },
      {
        path: 'ideas',
        name: 'IdeaLibrary',
        component: () => import('../views/IdeaLibrary.vue'),
        meta: { title: '创意灵感', group: '创作流程' }
      },
      {
        path: 'productions',
        name: 'ProductionList',
        component: () => import('../views/ProductionList.vue'),
        meta: { title: '视频创作', group: '创作流程' }
      },
      {
        path: 'productions/create',
        name: 'ProductionCreate',
        component: () => import('../views/ProductionEdit.vue'),
        meta: { title: '新建制作', group: '创作流程' }
      },
      {
        path: 'productions/:id/edit',
        name: 'ProductionEditPage',
        component: () => import('../views/ProductionEdit.vue'),
        meta: { title: '编辑制作', group: '创作流程' }
      },
      {
        path: 'publish-stats',
        name: 'PublishStats',
        component: () => import('../views/PublishStats.vue'),
        meta: { title: '数据中心', group: '创作流程' }
      },
      {
        path: 'publish-accounts',
        name: 'PublishAccounts',
        component: () => import('../views/PublishAccounts.vue'),
        meta: { title: '我的账号', group: '我的' }
      },
      {
        path: 'characters',
        name: 'CharacterLibrary',
        component: () => import('../views/CharacterLibrary.vue'),
        meta: { title: '人物资产', group: '资产库', assetType: 'character' }
      },
      {
        path: 'materials',
        name: 'MaterialSharing',
        component: () => import('../views/MaterialSharing.vue'),
        meta: { title: '素材共享', group: '资产库' }
      },
      {
        path: 'users',
        name: 'UserManagement',
        component: () => import('../views/UserManagement.vue'),
        meta: { title: '用户管理', group: '系统', adminOnly: true }
      },
      {
        path: 'settings',
        name: 'SystemSettings',
        component: () => import('../views/SystemSettings.vue'),
        meta: { title: '配置中心', group: '系统', adminOnly: true }
      },
      {
        path: 'roles',
        name: 'roles',
        component: () => import('../views/RolePermissions.vue'),
        meta: { title: '角色权限', group: '系统', adminOnly: true }
      }
    ]
  },
  { path: '/:pathMatch(.*)*', redirect: '/dashboard' }
]

const router = createRouter({ history: createWebHistory(), routes })

router.beforeEach(async (to) => {
  const token = readToken()
  if (to.meta.public) {
    if (token && to.path === '/login') return '/dashboard'
    return true
  }
  if (!token) return { path: '/login', query: { redirect: to.fullPath } }

  // 管理员专属页面：非超管回落到首页（用户管理 / 配置中心 / 角色权限）
  if (to.meta.adminOnly) {
    const user = readUser()
    if (!user || user.role !== 'admin') return '/dashboard'
  }

  // 模块角色菜单权限：先拉取当前用户权限，再按映射后的菜单 key 校验。
  // 注意：dashboard 是所有角色的落地页，永不自我重定向，否则登录后会无限跳转。
  const menuKey = ROUTE_NAME_TO_MENU[to.name]
  if (menuKey && menuKey !== 'dashboard' && ROUTE_MENU_KEYS.includes(menuKey)) {
    try {
      const perm = usePermissionStore()
      await perm.load()
      if (perm.role !== 'super' && !perm.loaded && !perm.menus.length) {
        // 身份尚未就绪时放行，避免误判；后端接口仍会做最终校验
        return true
      }
      if (!perm.canMenu(menuKey)) return '/dashboard'
    } catch (e) {
      /* 权限读取异常时放行，由后端接口做最终校验 */
    }
  }
  return true
})

export default router

