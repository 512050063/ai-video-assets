/**
 * 抖音数据采集（浏览器通道）
 *
 * 复用 frontend/node_modules 里的 playwright，用持久化用户目录保存登录态。
 * 脚本通过 stdin 接收 JSON 参数，结果以最后一行 JSON 输出到 stdout。
 *
 * action:
 * - login    打开有头浏览器供用户扫码 / 过滑块
 * - account  按抖音号 / 主页链接取账号资料
 * - videos   按主页链接 / sec_uid 取账号作品列表（播放数据）
 * - video    按作品链接取单条视频数据
 */
import fs from 'node:fs'
import path from 'node:path'
import { createRequire } from 'node:module'

const require = createRequire(import.meta.url)
const profileDir = process.env.DOYIN_PROFILE_DIR || path.resolve('data/douyin_profile')
fs.mkdirSync(profileDir, { recursive: true })

const UA =
  'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ' +
  '(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'

function out(obj) {
  process.stdout.write(JSON.stringify(obj) + '\n')
}

function readStdin() {
  return new Promise((resolve) => {
    let buf = ''
    process.stdin.setEncoding('utf8')
    process.stdin.on('data', (d) => (buf += d))
    process.stdin.on('end', () => resolve(buf))
  })
}

function loadChromium() {
  const candidates = [
    'playwright',
    'playwright-core',
    path.join(process.env.NODE_PATH || '', 'playwright'),
  ]
  for (const name of candidates) {
    try {
      return require(name).chromium
    } catch (_) {
      /* 继续尝试下一个 */
    }
  }
  throw new Error('未找到 playwright，请先在 frontend 目录执行 npm install')
}

/** 验证码中间页识别：抖音风控会替换页面为 __vc_is_render__ 中间页 */
async function isCaptcha(page) {
  try {
    const title = await page.title()
    if (/验证码|安全验证|captcha/i.test(title)) return true
    return await page.evaluate(() => {
      if (window.__vc_is_render__) return true
      const body = (document.body && document.body.innerText) || ''
      return /请完成验证|滑动验证|安全验证/.test(body.slice(0, 500))
    })
  } catch (_) {
    return false
  }
}

function captchaResult(hint) {
  return {
    ok: false,
    need_login: true,
    message: '抖音触发了安全验证（验证码中间页），自动采集已暂停',
    manual_hint: hint || '请在「我的账号」页点击「抖音验证」，在弹出的浏览器中完成验证后重试',
  }
}

/** 从页面里捞出内嵌 JSON */
function extractJson(page) {
  return page.evaluate(() => {
    const keys = [
      '__UNIVERSAL_DATA_FOR_REHYDRATION__',
      'RENDER_DATA',
      '_ROUTER_DATA',
      '__INITIAL_STATE__',
    ]
    for (const key of keys) {
      const raw = window[key]
      if (!raw) continue
      try {
        if (typeof raw === 'string') return JSON.parse(decodeURIComponent(raw))
        return raw
      } catch (_) {
        /* 换下一个 key */
      }
    }
    return null
  })
}

/** 递归收集所有用户节点（搜索接口 / 内嵌 JSON 通用） */
function collectUsers(node, outList, depth = 0) {
  if (!node || depth > 8 || outList.length > 40) return
  if (Array.isArray(node)) {
    for (const item of node) collectUsers(item, outList, depth + 1)
    return
  }
  if (typeof node !== 'object') return
  if (node.nickname && (node.unique_id || node.short_id || node.sec_uid)) outList.push(node)
  if (node.user && node.user.nickname) outList.push(node.user)
  for (const key of Object.keys(node)) {
    if (key === 'user') continue
    collectUsers(node[key], outList, depth + 1)
  }
}

function findAweme(node, depth = 0) {
  if (!node || depth > 8) return null
  if (Array.isArray(node)) {
    for (const item of node) {
      const hit = findAweme(item, depth + 1)
      if (hit) return hit
    }
    return null
  }
  if (typeof node !== 'object') return null
  if (node.statistics && (node.desc !== undefined || node.author)) return node
  if (node.aweme_id && node.statistics) return node
  for (const key of Object.keys(node)) {
    const hit = findAweme(node[key], depth + 1)
    if (hit) return hit
  }
  return null
}

function parseCount(v) {
  if (v === null || v === undefined) return 0
  if (typeof v === 'number') return Math.trunc(v)
  const s = String(v).trim()
  if (!s) return 0
  if (/^\d+$/.test(s)) return Number(s)
  const wan = s.match(/([\d.]+)\s*万/)
  if (wan) return Math.round(parseFloat(wan[1]) * 10000)
  const yi = s.match(/([\d.]+)\s*亿/)
  if (yi) return Math.round(parseFloat(yi[1]) * 100000000)
  const n = s.match(/[\d.]+/)
  return n ? Math.round(parseFloat(n[0])) : 0
}

function normalizeUser(user, homeUrl) {
  const avatar =
    (user.avatar_larger && user.avatar_larger.url_list && user.avatar_larger.url_list[0]) ||
    (user.avatar_thumb && user.avatar_thumb.url_list && user.avatar_thumb.url_list[0]) ||
    ''
  return {
    name: user.nickname || '',
    avatar,
    douyin_uid: user.unique_id || user.short_id || '',
    sec_uid: user.sec_uid || '',
    followers_count: parseCount(user.follower_count ?? user.mplatform_followers_count),
    likes_count: parseCount(user.total_favorited ?? user.mplatform_favoriting),
    video_count: parseCount(user.aweme_count ?? user.mplatform_video_count),
    home_url: user.home_url || homeUrl || '',
  }
}

function normalizeAweme(a) {
  const stat = a.statistics || {}
  const cover =
    (a.video && a.video.cover && a.video.cover.url_list && a.video.cover.url_list[0]) ||
    (a.video && a.video.origin_cover && a.video.origin_cover.url_list && a.video.origin_cover.url_list[0]) ||
    ''
  return {
    video_id: String(a.aweme_id || ''),
    title: String(a.desc || '').replace(/\s*#\S+/g, '').trim(),
    tags: (String(a.desc || '').match(/#([^\s#]+)/g) || []).map((t) => t.slice(1)),
    cover,
    author: (a.author && a.author.nickname) || '',
    author_id: (a.author && (a.author.unique_id || a.author.short_id)) || '',
    plays: parseCount(stat.play_count ?? stat.playCount),
    likes: parseCount(stat.digg_count ?? stat.diggCount),
    comments: parseCount(stat.comment_count ?? stat.commentCount),
    shares: parseCount(stat.share_count ?? stat.shareCount),
    collects: parseCount(stat.collect_count ?? stat.collectCount),
    create_time: a.create_time || 0,
  }
}

function fail(message, hint, needLogin = false) {
  out({ ok: false, need_login: needLogin, message, manual_hint: hint || '可改用手工录入' })
}

/** 扫码完成后读取当前登录账号资料（尽力而为，取不到不影响登录态保存） */
async function readSelfUser(page) {
  let selfUser = null
  const onResponse = async (resp) => {
    if (!/\/aweme\/v1\/web\/(user\/profile\/self|im\/user\/info)/.test(resp.url())) return
    try {
      const json = await resp.json()
      const user = json && (json.user || (json.data && json.data.user))
      if (user && user.nickname) selfUser = user
    } catch (_) {
      /* 忽略非 JSON 响应 */
    }
  }
  page.on('response', onResponse)
  try {
    await page.goto('https://www.douyin.com/', { waitUntil: 'domcontentloaded', timeout: 30000 })
    for (let i = 0; i < 12 && !selfUser; i++) await page.waitForTimeout(500)
    if (!selfUser) {
      const embedded = await extractJson(page)
      const users = []
      collectUsers(embedded, users)
      selfUser = users.find((u) => u.nickname && (u.sec_uid || u.follower_count !== undefined)) || null
    }
    if (!selfUser) {
      const domName = await page.evaluate(() => {
        const el = document.querySelector('[data-e2e="user-name"], [class*="user-name"]')
        return el ? (el.innerText || el.textContent || '').trim() : ''
      })
      if (domName) selfUser = { nickname: domName.slice(0, 60) }
    }
  } catch (_) {
    /* 读取失败时仍保留已保存的登录态 */
  } finally {
    page.off('response', onResponse)
  }
  return selfUser ? normalizeUser(selfUser, 'https://www.douyin.com/') : null
}

async function main() {
  const action = process.argv[2] || 'video'
  let payload = {}
  try {
    payload = JSON.parse((await readStdin()) || '{}')
  } catch (_) {
    /* 空参数 */
  }

  const chromium = loadChromium()
  const headless = process.env.DOYIN_HEADLESS === '1'
  const context = await chromium.launchPersistentContext(profileDir, {
    headless,
    viewport: { width: 1440, height: 900 },
    userAgent: UA,
    locale: 'zh-CN',
    args: ['--disable-blink-features=AutomationControlled'],
  })
  const page = context.pages()[0] || (await context.newPage())

  // 监听关键 XHR：详情 / 搜索用户 / 用户主页资料 / 用户作品列表
  const live = { detail: null, users: [], profile: null, posts: [] }
  page.on('response', async (resp) => {
    try {
      const url = resp.url()
      let json = null
      if (/\/aweme\/v1\/web\/aweme\/detail/.test(url)) {
        json = await resp.json()
        if (json && json.aweme_detail) live.detail = json.aweme_detail
      } else if (/\/aweme\/v1\/web\/(general\/search|discover\/search|user\/search)/.test(url)) {
        json = await resp.json()
        const arr = (json && json.data) || []
        collectUsers(arr, live.users)
      } else if (/\/aweme\/v1\/web\/user\/profile\/other/.test(url)) {
        json = await resp.json()
        if (json && json.user) live.profile = json.user
      } else if (/\/aweme\/v1\/web\/aweme\/post/.test(url)) {
        json = await resp.json()
        const list = (json && json.aweme_list) || []
        for (const a of list) {
          if (a && a.aweme_id && !live.posts.some((x) => x.aweme_id === a.aweme_id)) live.posts.push(a)
        }
      }
    } catch (_) {
      /* 忽略非 JSON 或已失效响应 */
    }
  })

  try {
    if (action === 'login') {
      await page.goto(payload.url || 'https://www.douyin.com/', { waitUntil: 'domcontentloaded', timeout: 45000 })
      // 轮询登录 Cookie：用户扫码成功后自动结束，无需手动关闭窗口。
      // 登录态会持久化到该账号专属目录，供后续采集直接复用。
      let logged = false
      for (let i = 0; i < 170; i++) {
        try {
          const cookies = await context.cookies()
          logged = cookies.some((c) => /^(sessionid|sessionid_ss)$/.test(c.name) && c.value)
        } catch (_) {
          break
        }
        if (logged || page.isClosed()) break
        await new Promise((resolve) => setTimeout(resolve, 1000))
      }
      if (!logged) {
        out({
          ok: false,
          need_login: true,
          message: '未检测到登录态，请在浏览器中完成扫码登录',
          manual_hint: '重新点击「扫码登录」，完成扫码后等待页面自动跳转，窗口会自行关闭',
        })
        return
      }
      let self = null
      try {
        const livePage = page.isClosed() ? await context.newPage() : page
        self = await readSelfUser(livePage)
      } catch (_) {
        /* 读取用户信息失败不影响登录态保存 */
      }
      out({
        ok: true,
        data: {
          logged_in: true,
          name: (self && self.name) || '',
          douyin_uid: (self && self.douyin_uid) || '',
          sec_uid: (self && self.sec_uid) || '',
          avatar: (self && self.avatar) || '',
          followers_count: (self && self.followers_count) || 0,
          likes_count: (self && self.likes_count) || 0,
          video_count: (self && self.video_count) || 0,
          profile_key: payload.profile_key || '',
          message: '登录态已保存到本机，可以开始自动采集',
        },
      })
      return
    }

    const target = payload.url || ''
    if (!target) {
      fail(action === 'account' ? '缺少抖音号或主页链接' : '缺少作品链接')
      return
    }

    await page.goto(target, { waitUntil: 'domcontentloaded', timeout: 45000 })
    await page.waitForTimeout(2500)
    if (await isCaptcha(page)) {
      out(captchaResult())
      return
    }

    if (action === 'account') {
      // 等待搜索 / 主页资料接口返回
      for (let i = 0; i < 14 && !live.users.length && !live.profile; i++) await page.waitForTimeout(500)
      if (await isCaptcha(page)) {
        out(captchaResult())
        return
      }
      const data = await extractJson(page)
      const embedded = []
      collectUsers(data, embedded)
      const users = [...live.users, ...(live.profile ? [live.profile] : []), ...embedded]
      const want = String(payload.douyin_uid || '').toLowerCase()
      const matched = users.find(
        (u) => want && String(u.unique_id || u.short_id || '').toLowerCase() === want
      ) || users.find((u) => u.follower_count !== undefined || u.mplatform_followers_count !== undefined) || users[0]
      if (!matched) {
        fail(
          '页面未返回账号数据，可能未登录或触发了验证',
          '请在「我的账号」页点击「抖音验证」完成验证后重试，或直接填写主页链接',
          true
        )
        return
      }
      out({ ok: true, data: normalizeUser(matched, target) })
      return
    }

    if (action === 'videos') {
      for (let i = 0; i < 16 && live.posts.length < (payload.limit || 10); i++) {
        await page.waitForTimeout(500)
        if (i % 4 === 3) await page.mouse.wheel(0, 1600).catch(() => {})
      }
      if (await isCaptcha(page)) {
        out(captchaResult())
        return
      }
      if (!live.posts.length) {
        fail('未获取到作品列表，可能未登录或主页链接无效', '请填写主页链接（https://www.douyin.com/user/...）或先完成抖音验证', true)
        return
      }
      const limit = Number(payload.limit || 10)
      out({
        ok: true,
        data: {
          sec_uid: (live.profile && live.profile.sec_uid) || payload.sec_uid || '',
          name: (live.profile && live.profile.nickname) || '',
          videos: live.posts.slice(0, limit).map(normalizeAweme),
        },
      })
      return
    }

    // video：单条作品（创意库解析沿用）
    for (let i = 0; i < 16 && !live.detail; i++) await page.waitForTimeout(500)
    if (await isCaptcha(page)) {
      out(captchaResult('请在「创意灵感」页重新解析，或先在「我的账号」页完成抖音验证'))
      return
    }
    const data = await extractJson(page)
    const aweme = live.detail || (data ? findAweme(data) : null)
    if (!aweme) {
      fail('页面未返回作品数据，可能未登录或触发了验证', '请完成抖音验证后重试，或手工录入', true)
      return
    }
    out({ ok: true, data: normalizeAweme(aweme) })
  } catch (err) {
    fail(String((err && err.message) || err))
  } finally {
    await context.close().catch(() => {})
  }
}

main().catch((err) => {
  out({ ok: false, message: String((err && err.message) || err), manual_hint: '可改用手工录入' })
  process.exit(0)
})
