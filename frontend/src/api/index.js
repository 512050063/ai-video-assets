import axios from 'axios'
import { clearSession, readToken } from '../utils/session'

export const api = axios.create({ baseURL: '/api', timeout: 60000 })

api.interceptors.request.use((config) => {
  const token = readToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res,
  (error) => {
    if (error.response && error.response.status === 401) {
      clearSession()
      if (!location.pathname.startsWith('/login')) {
        location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

/* ================= 创意库 ================= */
// 全流程 6 态：权威状态放创意；「备选库」改为独立备选标记 is_backup，不再是流程状态
export const IDEA_STATUS_OPTIONS = [
  { value: '未使用', type: 'info', label: '未使用' },
  { value: '已排期', type: 'warning', label: '已排期' },
  { value: '制作中', type: 'primary', label: '制作中' },
  { value: '待发布', type: 'warning', label: '待发布' },
  { value: '搁置中', type: 'info', label: '已搁置' },
  { value: '已完成', type: 'success', label: '已发布' }
]
// 创意灵感页状态标签可直接切换的两态
export const IDEA_STATUS_DIRECT = ['未使用', '已排期']

export function ideaStatusType(status) {
  const found = IDEA_STATUS_OPTIONS.find((s) => s.value === status)
  return found ? found.type : 'info'
}

// 展示文案：内部状态值「已完成」对外显示为「已发布」，与其他模块（视频创作 / 发布数据）一致
export function ideaStatusLabel(status) {
  const found = IDEA_STATUS_OPTIONS.find((s) => s.value === status)
  return found ? found.label : (status || '')
}

/* ================= 创作排期优先级 ================= */
export const PLAN_PRIORITY_OPTIONS = [
  { value: 1, label: '高', type: 'danger' },
  { value: 2, label: '中', type: 'warning' },
  { value: 3, label: '低', type: 'info' }
]

export function planPriorityType(priority) {
  const found = PLAN_PRIORITY_OPTIONS.find((s) => s.value === priority)
  return found ? found.type : 'info'
}

export function planPriorityLabel(priority) {
  const found = PLAN_PRIORITY_OPTIONS.find((s) => s.value === priority)
  return found ? found.label : '中'
}

/* ================= 视频制作 ================= */
// 制作四态与创意全流程后四态一致：制作中 → 待发布 → 搁置中 / 已完成
export const PRODUCTION_STATUS_OPTIONS = [
  { value: '制作中', type: 'warning', label: '制作中' },
  { value: '待发布', type: 'primary', label: '待发布' },
  { value: '已完成', type: 'success', label: '已发布' }
]

// 创作平台
export const PLATFORM_OPTIONS = [
  { value: '硬核', label: '硬核', color: '#4a7cc4' },
  { value: '小云雀', label: '小云雀', color: '#7b62c9' },
  { value: '三方平台', label: '三方平台', color: '#3da377' }
]

export function productionStatusType(status) {
  const found = PRODUCTION_STATUS_OPTIONS.find((s) => s.value === status)
  return found ? found.type : 'info'
}

// 展示文案：内部状态值「已完成」对外显示为「已发布」，「搁置中」显示为「已搁置」
export function productionStatusLabel(status) {
  if (status === '已完成') return '已发布'
  if (status === '搁置中') return '已搁置'
  return status || ''
}

/* ================= 数据中心记录状态 ================= */
export const DATA_STATUS_OPTIONS = [
  { value: '正常', type: 'success', label: '正常' },
  { value: '隐藏', type: 'warning', label: '隐藏' }
]

export function dataStatusType(status) {
  const found = DATA_STATUS_OPTIONS.find((s) => s.value === status)
  return found ? found.type : 'info'
}

/* ================= 我的账号 ================= */
export const ACCOUNT_STATUS_OPTIONS = [
  { value: '正常', type: 'success', label: '正常' },
  { value: '搁置', type: 'warning', label: '搁置' },
  { value: '废弃', type: 'info', label: '废弃' }
]

export const UPDATE_RHYTHM_OPTIONS = ['日更', '隔日更', '周更']

export function accountStatusType(status) {
  const found = ACCOUNT_STATUS_OPTIONS.find((s) => s.value === status)
  return found ? found.type : 'info'
}

export function platformLabel(platform) {
  return platform || '未标注'
}

/* ================= 人物资产 ================= */
export const CHARACTER_ROLES = ['主角', '配角', '替身', '出镜']

/* ================= 提示词 ================= */
// 提示词默认分段（对标 Excel 中的【人物背景】【场景背景】【人物着装】等）
export const DEFAULT_PROMPT_SEGS = ['人物背景', '场景背景', '人物着装', '镜头背景']

/* ================= 附件类型 ================= */
export const ASSET_TYPES = [
  { value: 'cover', label: '封面截图', accept: 'image/*', listType: 'picture-card' },
  { value: 'reference_shot', label: '参考视频截图', accept: 'image/*', listType: 'picture-card' },
  { value: 'output', label: '生成视频', accept: 'video/mp4,video/*', listType: 'text' }
]

/* ================= 通用 ================= */
export function formatDateTime(value, fallback = '—') {
  if (!value) return fallback
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return fallback
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ${p(d.getHours())}:${p(d.getMinutes())}`
}

export function formatDate(value, fallback = '—') {
  if (!value) return fallback
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return fallback
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
