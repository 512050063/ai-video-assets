/**
 * 抖音数据采集（浏览器通道）
 *
 * 复用 frontend/node_modules 里的 playwright，用持久化用户目录保存登录态。
 * 脚本通过 stdin 接收 JSON 参数，结果以最后一行 JSON 输出到 stdout。
 *
 * action:
 * - login    打开浏览器供用户扫码 / 过滑块（DOYIN_QR_MODE=1 时无头并把二维码回传）
 * - account  按抖音号 / 主页链接取账号资料
 * - videos   按主页链接 / sec_uid 取账号作品列表（播放数据）
 * - video    按作品链接取单条视频数据
 *
 * DOYIN_QR_MODE=1 时，登录流程会先输出一行 `__QR__{...}`（base64 图片），
 * 再输出最终的 JSON 结果；Python 端按行解析即可把二维码推给远程用户。
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

/** 远程扫码：把二维码图片作为独立事件行输出，不干扰最终 JSON 结果 */
function qrEvent(obj) {
  process.stdout.write('__QR__' + JSON.stringify(obj) + '\n')
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

/**
 * 抖音登录弹窗二维码的真实结构（线上实测）：
 *   <div id="douyin_login_comp_scan_code_qrcode">
 *     <img src="data:image/png;base64,...">   // 512x512 PNG 原图
 *   </div>
 * 直接读取 img.src 就能拿到高清原图，比整页截图清晰得多，也不需要截图等待。
 */
const QR_SELECTORS = [
  '#douyin_login_comp_scan_code_qrcode img',
  '[id*="qrcode"] img',
  '[class*="qrcode"] img',
  '[data-e2e*="qr"] img',
  'img[src^="data:image"]',
]

/** 登录弹窗容器：抓不到二维码时只截弹窗，不截整页 */
const LOGIN_PANEL_SELECTORS = [
  '#login-panel-new',
  '[id*="login-panel"]',
  '[class*="login-panel"]',
]

function stripDataUrl(src) {
  return String(src || '').replace(/^data:image\/[A-Za-z0-9.+-]+;base64,/, '')
}

/**
 * 一次性 evaluate 扫描所有 frame，直接拿到二维码图片数据。
 * 刻意不使用 locator.waitFor：抖音弹窗渲染慢，串行 waitFor 每个选择器要等满
 * 2.5 秒，10 个选择器就是 25 秒，这是之前「20 秒才出图」的根源。
 */
async function captureQrImage(page) {
  for (const frame of page.frames()) {
    let found = null
    try {
      found = await frame.evaluate((selectors) => {
        const seen = new Set()
        for (const sel of selectors) {
          for (const el of document.querySelectorAll(sel)) {
            if (seen.has(el)) continue
            seen.add(el)
            const r = el.getBoundingClientRect()
            // 过滤小图标和大背景图，只留二维码尺寸范围
            if (r.width < 60 || r.height < 60 || r.width > 600 || r.height > 600) continue
            const src = String(el.src || el.getAttribute('src') || '')
            if (!src) continue
            if (el.tagName === 'IMG' && /^data:image\//i.test(src)) {
              return { data: src, source: 'dataurl' }
            }
            if (el.tagName === 'IMG' && /^https?:\/\//i.test(src)) {
              return { data: src, source: 'url' }
            }
            if (el.tagName === 'CANVAS') {
              try {
                return { data: el.toDataURL('image/png'), source: 'dataurl' }
              } catch (_) { /* 换下一个元素 */ }
            }
          }
        }
        return null
      }, QR_SELECTORS)
    } catch (_) {
      continue
    }
    if (!found) continue

    // 远程图片：在浏览器里转成 data URL，避开 CORS 与后端二次下载
    if (found.source === 'url') {
      const dataUrl = await frame.evaluate(async (url) => {
        try {
          const resp = await fetch(url, { mode: 'cors' })
          const blob = await resp.blob()
          return await new Promise((resolve) => {
            const reader = new FileReader()
            reader.onload = () => resolve(String(reader.result || ''))
            reader.onerror = () => resolve('')
            reader.readAsDataURL(blob)
          })
        } catch (_) {
          return ''
        }
      }, found.data).catch(() => '')
      if (dataUrl) found.data = dataUrl
      else continue
    }
    return { data: stripDataUrl(found.data), kind: 'qr', source: found.source }
  }
  return null
}

/** 回退：只截登录弹窗（约 726x483），比整页截图的二维码占比高很多 */
async function captureLoginPanel(page) {
  for (const frame of page.frames()) {
    try {
      const info = await frame.evaluate((selectors) => {
        for (const sel of selectors) {
          const el = document.querySelector(sel)
          if (!el) continue
          const r = el.getBoundingClientRect()
          if (r.width >= 200 && r.height >= 150) return { selector: sel }
        }
        return null
      }, LOGIN_PANEL_SELECTORS)
      if (!info) continue
      const buffer = await frame.locator(info.selector).first().screenshot({ timeout: 5000 })
      if (buffer && buffer.length > 800) {
        return { data: buffer.toString('base64'), kind: 'page' }
      }
    } catch (_) { /* 换下一个 frame */ }
  }
  return null
}

/** 首页默认不展开登录框，点一下「登录」让二维码出现 */
async function tryOpenLoginModal(page) {
  for (const frame of page.frames()) {
    try {
      const clicked = await frame.evaluate((texts) => {
        const nodes = [...document.querySelectorAll('button,[role="button"],a')]
        for (const text of texts) {
          const el = nodes.find((n) => (n.innerText || '').trim() === text && n.getClientRects().length)
          if (el) {
            el.click()
            return true
          }
        }
        return false
      }, ['登录', '扫码登录', '立即登录', '登录/注册'])
      if (clicked) return true
    } catch (_) {
      /* 换下一个 frame */
    }
  }
  return false
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

/**
 * 抖音主页滚动容器不是 document.body，单纯 page.mouse.wheel 只能触发第一页。
 * 找到页面上最大可滚动容器并滚到底，同时兼容 wheel，触发后续作品分页请求。
 */
async function scrollVideoFeed(page) {
  await page.evaluate(() => {
    const candidates = []
    for (const el of document.querySelectorAll('*')) {
      const sh = el.scrollHeight || 0
      const ch = el.clientHeight || 0
      if (sh > ch + 50 && ch > 200) candidates.push({ el, size: sh - ch })
    }
    candidates.sort((a, b) => b.size - a.size)
    if (candidates[0]) candidates[0].el.scrollTop = candidates[0].el.scrollHeight
    if (document.scrollingElement) document.scrollingElement.scrollTop = document.scrollingElement.scrollHeight
  }).catch(() => {})
  await page.mouse.wheel(0, 2200).catch(() => {})
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
    // 时长：抖音详情以毫秒给出（video.duration / duration），统一换算成秒
    duration: (() => {
      const ms = Number((a.video && a.video.duration) || a.duration || 0) || 0
      return ms > 0 ? Math.round((ms / 1000) * 10) / 10 : 0
    })(),
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
  const live = { detail: null, users: [], profile: null, posts: [], postHasMore: true, postPages: 0 }
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
        live.postPages += 1
        // has_more=0 表示抖音已返回全部公开作品，继续滚动没有意义。
        live.postHasMore = json && json.has_more !== undefined ? !!json.has_more : true
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

      // 远程扫码模式：直接读取二维码 img 的高清原图（512x512）推给网页端。
      // 抖音登录弹窗通常 10~15 秒才渲染出二维码，每 400ms 扫一次，出现即推送。
      let lastQr = ''
      if (process.env.DOYIN_QR_MODE === '1') {
        let sent = false
        for (let i = 0; i < 75; i++) {
          const qr = await captureQrImage(page)
          if (qr) {
            qrEvent(qr)
            lastQr = qr.data
            sent = true
            break
          }
          if (i % 5 === 0) await tryOpenLoginModal(page)
          await sleep(400)
        }
        if (!sent) {
          // 抓不到二维码时只截登录弹窗，比 1440x900 整页截图清晰得多
          const panel = await captureLoginPanel(page)
          if (panel) qrEvent(panel)
          else {
            try {
              const buffer = await page.screenshot({ timeout: 10000 })
              qrEvent({ data: buffer.toString('base64'), kind: 'page' })
            } catch (_) {
              /* 截图失败不影响后续登录态轮询 */
            }
          }
        }
      }

      // 轮询登录 Cookie：用户扫码成功后自动结束，无需手动关闭窗口。
      // 二维码会过期，等待期间持续检测刷新并推送新图，避免用户扫到失效的码。
      let logged = false
      for (let i = 0; i < 170; i++) {
        try {
          const cookies = await context.cookies()
          logged = cookies.some((c) => /^(sessionid|sessionid_ss)$/.test(c.name) && c.value)
        } catch (_) {
          break
        }
        if (logged || page.isClosed()) break
        if (process.env.DOYIN_QR_MODE === '1' && lastQr && i % 5 === 0) {
          const fresh = await captureQrImage(page)
          if (fresh && fresh.data !== lastQr) {
            qrEvent(fresh)
            lastQr = fresh.data
          }
        }
        await sleep(1000)
      }
      if (!logged) {
        out({
          ok: false,
          need_login: true,
          message: '未检测到登录态，请在页面中完成扫码登录',
          manual_hint: process.env.DOYIN_QR_MODE === '1'
            ? '请用手机抖音扫描页面上的二维码；若超时可重新点击「扫码登录」或改用手动添加'
            : '重新点击「扫码登录」，完成扫码后等待页面自动跳转，窗口会自行关闭',
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
      const limit = Number(payload.limit || 10)
      // 前 2.5 秒等首屏作品接口；之后滚动加载直到达到目标条数或抖音返回完。
      const deadline = Date.now() + 45000
      let lastCount = live.posts.length
      let idleRounds = 0
      for (let i = 0; i < 90 && live.posts.length < limit && Date.now() < deadline; i++) {
        await page.waitForTimeout(450)
        if (live.posts.length > lastCount) {
          lastCount = live.posts.length
          idleRounds = 0
        } else {
          idleRounds += 1
        }
        if (i % 2 === 0) await scrollVideoFeed(page)
        // has_more=0 时再观察几轮，避免并发请求尚未落地；之后提前结束。
        if (!live.postHasMore && live.postPages > 0 && idleRounds >= 6) break
        if (idleRounds >= 24) break
      }
      if (await isCaptcha(page)) {
        out(captchaResult())
        return
      }
      if (!live.posts.length) {
        fail('未获取到作品列表，可能未登录或主页链接无效', '请填写主页链接（https://www.douyin.com/user/...）或先完成抖音验证', true)
        return
      }
      const collected = live.posts.slice(0, limit)
      // list_complete：本次是否抓到了公开作品列表末尾（未被 limit 截断且抖音返回 has_more=0）。
      // 只有完整采集才能安全地用「差集」判断隐藏视频，否则会把未抓到的正常视频误标为隐藏。
      const listComplete = !live.postHasMore && live.postPages > 0
      out({
        ok: true,
        data: {
          sec_uid: (live.profile && live.profile.sec_uid) || payload.sec_uid || '',
          name: (live.profile && live.profile.nickname) || '',
          videos: collected.map(normalizeAweme),
          list_complete: listComplete,
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
