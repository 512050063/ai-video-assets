/* ================= 分类 / 制作平台 / 发布平台 统一选项 =================
 * 三者的颜色、图片图标与展示方式配置在「配置中心」，全局共用同一套解析逻辑。
 * - image：上传的图片 URL（不再定死内置图标）
 * - display：full 全显（图标 + 名称）/ label 仅标签 / icon 仅图标
 * 兼容旧配置里的 Element Plus 图标名 icon，缺失图片时可用其作为兜底展示。
 */
import {
  Connection,
  Monitor,
  MagicStick,
  Promotion,
  Star,
  VideoCamera,
  ChatDotRound,
  Picture,
  Film,
  Camera,
  Microphone,
  DataLine,
  Histogram,
  Trophy,
  Reading,
  Cellphone,
  Platform,
  Odometer,
  Lightning,
  Medal,
  Compass,
  Flag,
  Postcard,
  Discount,
  Wallet,
  Goods,
  Present
} from '@element-plus/icons-vue'

export const PLATFORM_ICON_MAP = {
  Monitor,
  MagicStick,
  Connection,
  Promotion,
  Star,
  VideoCamera,
  ChatDotRound,
  Picture,
  Film,
  Camera,
  Microphone,
  DataLine,
  Histogram,
  Trophy,
  Reading,
  Cellphone,
  Platform,
  Odometer,
  Lightning,
  Medal,
  Compass,
  Flag,
  Postcard,
  Discount,
  Wallet,
  Goods,
  Present
}

export const PLATFORM_ICON_OPTIONS = Object.keys(PLATFORM_ICON_MAP)

export const DEFAULT_PRODUCTION_ICON = 'Monitor'
export const DEFAULT_PUBLISH_ICON = 'Promotion'

// 展示方式：全显 / 标签 / 图标
export const PLATFORM_DISPLAY_MODES = [
  { value: 'full', label: '全显' },
  { value: 'label', label: '标签' },
  { value: 'icon', label: '图标' }
]

export function normalizeDisplay(value) {
  return value === 'label' || value === 'icon' ? value : 'full'
}

export function displayLabel(value) {
  const found = PLATFORM_DISPLAY_MODES.find((m) => m.value === normalizeDisplay(value))
  return found ? found.label : '全显'
}

/**
 * 归一化平台 / 分类选项：{ name, color, image, display, icon }
 * 兼容字符串配置与旧版 icon 组件名。
 */
export function normalizeOption(item, fallbackColor = '#7b62c9') {
  if (typeof item === 'string') {
    return { id: null, name: item, color: fallbackColor, image: '', display: 'full', icon: '' }
  }
  const src = item || {}
  return {
    id: src.id || null,
    name: src.name || '',
    color: src.color || fallbackColor,
    image: src.image || '',
    display: normalizeDisplay(src.display || 'full'),
    icon: src.icon || ''
  }
}

/** 兼容旧调用：取得图标组件（图片模式优先由 OptionBadge 渲染 <img>） */
export function resolvePlatformIcon(name, fallback = DEFAULT_PRODUCTION_ICON) {
  if (name && PLATFORM_ICON_MAP[name]) return PLATFORM_ICON_MAP[name]
  return PLATFORM_ICON_MAP[fallback] || Monitor
}

/** 兼容旧调用：全局 platform_display 已下沉为每项独立 display，这里仅作兜底 */
export function platformDisplayMode(settings) {
  return normalizeDisplay(settings?.platform_display?.mode)
}

/* ================= 模块角色与权限 ================= */
export const MODULE_ROLES = [
  { value: 'super', label: '超管', desc: '全量权限：所有菜单与按钮' },
  { value: 'inspiration', label: '灵感', desc: '创意收集与讨论、资产维护' },
  { value: 'production', label: '创作', desc: '创意排期、视频制作与发布数据' },
  { value: 'operation', label: '运营', desc: '发布账号、发布数据与成片运营' }
]

export function moduleRoleLabel(key) {
  const found = MODULE_ROLES.find((r) => r.value === key)
  return found ? found.label : key
}

export function moduleRoleType(key) {
  const map = { super: 'danger', inspiration: 'warning', production: 'primary', operation: 'success' }
  return map[key] || 'info'
}
