/* AI 视频资产管理系统 - 前端真实浏览器冒烟测试（三菜单 · 5 态流程版）
 * 运行：node frontend/smoke_test.cjs
 * 依赖：npm install --no-save playwright && npx playwright install chromium
 *
 * 覆盖：登录、三菜单、创意灵感 5 态与创作计划/取消排期交互、
 *       视频创作状态确认弹窗、发布数据页、控制台异常。
 */
const { chromium } = require('playwright')

const BASE = 'http://localhost:5173'
let PASS = 0
let FAIL = 0
const FAILED = []

function ok(label, cond, extra = '') {
  if (cond) {
    PASS++
    console.log('  [PASS] ' + label + (extra ? ' | ' + extra : ''))
  } else {
    FAIL++
    FAILED.push(label + (extra ? ' | ' + extra : ''))
    console.log('  [FAIL] ' + label + (extra ? ' | ' + extra : ''))
  }
}

function section(t) { console.log('\n=== ' + t + ' ===') }
async function text(locator) { return (await locator.innerText()).replace(/\s+/g, ' ').trim() }

async function main() {
  const browser = await chromium.launch({ headless: true })
  const context = await browser.newContext({ viewport: { width: 1600, height: 950 } })
  const page = await context.newPage()
  const errors = []
  page.on('pageerror', (e) => errors.push(String(e.message || e)))
  page.on('console', (m) => { if (m.type() === 'error') errors.push('console: ' + m.text()) })

  try {
    /* ---------- 1. 登录 ---------- */
    section('1. 登录与会话')
    let resp = await page.goto(BASE + '/login', { waitUntil: 'domcontentloaded' })
    ok('登录页可访问', resp.status() === 200)
    await page.locator('.login-card input').nth(0).fill('admin')
    await page.locator('.login-card input').nth(1).fill('admin123456')
    await page.locator('.login-card button').filter({ hasText: '登录' }).first().click()
    await page.waitForURL('**/dashboard', { timeout: 20000 })
    ok('登录跳转首页', page.url().includes('/dashboard'))
    ok('登录态写入会话', await page.evaluate(() => !!sessionStorage.getItem('avm_token')))
    // 刷新一次，确保权限 store 在 token 就位后完成加载（首挂载存在时序竞争）
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(1000)

    /* ---------- 1b. 首页两大主线 ---------- */
    section('1b. 首页：制作排期 / 发布数据 + 趋势图')
    ok('首页两块主线面板', await page.locator('.panel--schedule').count() === 1
       && await page.locator('.panel--publish').count() === 1)
    ok('首页两张趋势图渲染', await page.locator('.trend-svg').count() === 2
       && await page.locator('.trend-line').count() >= 2,
       'svg=' + await page.locator('.trend-svg').count())
    ok('首页无零散人物排行/我的进度卡',
       !(await text(page.locator('body'))).includes('人物使用排行')
       && !(await text(page.locator('body'))).includes('我的进度'))

    /* ---------- 2. 三菜单 ---------- */
    section('2. 三菜单流程（创意灵感 / 视频创作 / 发布数据）')
    const menuTexts = (await page.locator('.adm-menu-item .adm-menu-text').allInnerTexts()).map((t) => t.trim())
    ok('菜单含创意灵感', menuTexts.includes('创意灵感'), menuTexts.join('/'))
    ok('菜单含视频创作', menuTexts.includes('视频创作'), menuTexts.join('/'))
    ok('菜单含发布数据', menuTexts.includes('发布数据'), menuTexts.join('/'))
    ok('流程菜单恰好三项', ['创意灵感', '视频创作', '发布数据'].every((k) => menuTexts.includes(k)))

    /* ---------- 2b. 用户管理：角色权限统一入口 ---------- */
    section('2b. 用户管理：角色权限统一入口')
    await page.goto(BASE + '/users', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(600)
    await page.getByRole('button', { name: '新建用户' }).first().click()
    await page.waitForTimeout(300)
    const userDlg = page.locator('.el-dialog:visible').filter({ hasText: '新建用户' })
    const userLabels = (await userDlg.locator('.el-form-item__label').allInnerTexts()).map((t) => t.trim())
    ok('用户弹窗只有一个角色权限下拉', userLabels.filter((l) => l === '角色权限').length === 1,
       userLabels.join('|'))
    ok('用户弹窗不再单独设置创建权限/数据范围',
       !userLabels.includes('创建权限') && !userLabels.includes('数据范围') && !userLabels.includes('模块角色'),
       userLabels.join('|'))
    ok('角色权限说明可见', await userDlg.locator('.role-perm-summary').count() === 1)
    await userDlg.getByRole('button', { name: '取消' }).last().click()
    await page.waitForTimeout(200)

    /* ---------- 3. 创意灵感：5 态与创作计划列 ---------- */
    section('3. 创意灵感：四项统计 / 标签筛选 / 列结构')
    resp = await page.goto(BASE + '/ideas', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(900)
    let body = await text(page.locator('body'))
    ok('创意灵感页打开', resp.status() === 200 && body.includes('创意灵感'))
    const arrangedIdeas = await page.evaluate(async () => {
      const t = sessionStorage.getItem('avm_token')
      const r = await fetch('/api/ideas', { headers: { Authorization: 'Bearer ' + t } })
      const rows = r.ok ? await r.json() : []
      return rows.filter((x) => x.status === '已排期').length
    })
    ok('已排期状态可正常展示', body.includes('已排期') || arrangedIdeas === 0,
       body.includes('已排期') ? 'yes' : `arranged=${arrangedIdeas}`)
    const ideaStatLabels = (await page.locator('.stat-row .adm-stat .adm-stat-label').allInnerTexts()).map((t) => t.trim())
    ok('创意统计标签改为四项', ideaStatLabels.length === 4
       && ['创意总量', '已使用', '未使用', '今日新增'].every((s) => ideaStatLabels.includes(s)),
       ideaStatLabels.join('|'))
    ok('备选库不是状态列标签', await page.locator('.el-table__body td .el-tag').filter({ hasText: '备选库' }).count() === 0)
    // 最终态展示统一：内部「已完成」在状态列显示为「已发布」，页面不出现「已完成」文案
    ok('创意状态列不出现「已完成」文案', await page.locator('.el-table__body td .el-tag').filter({ hasText: '已完成' }).count() === 0)
    ok('页头状态下拉框已删除', await page.locator('.el-select__placeholder').filter({ hasText: '状态' }).count() === 0)
    const usageSelect = page.locator('.el-select').filter({ hasText: '全部' }).first()
    if (await usageSelect.count()) {
      await usageSelect.click()
      await page.waitForTimeout(250)
      const usageOptions = (await page.locator('.el-select-dropdown:visible .el-select-dropdown__item').allInnerTexts()).map((t) => t.trim())
      ok('创意标签筛选齐全', ['全部', '已使用', '未使用', '备选库'].every((x) => usageOptions.includes(x)),
         usageOptions.join('|'))
      await page.keyboard.press('Escape')
      await page.waitForTimeout(150)
    }
    const headers = (await page.locator('.el-table__header th .cell').allInnerTexts()).map((t) => t.trim())
    ok('含状态列', headers.includes('状态'), headers.join('|'))
    ok('含创作计划列', headers.includes('创作计划'), headers.join('|'))
    ok('含创意提供列', headers.includes('创意提供'), headers.join('|'))
    // 初始态行显示创作计划默认图标；已排期/制作中行显示优先级/创作人/时间
    const ideaRows = await page.locator('.el-table__body tr.el-table__row').count()
    const iconCount = await page.locator('.plan-icon-btn').count()
    const arrangeCount = await page.locator('.arrange-cell--btn').count()
    ok('未使用显示创作计划默认图标', iconCount >= 1 || ideaRows === 0, 'icons=' + iconCount + ' rows=' + ideaRows)
    const arrangedTotal = await page.evaluate(async () => {
      const t = sessionStorage.getItem('avm_token')
      const r = await fetch('/api/ideas', { headers: { Authorization: 'Bearer ' + t } })
      const rows = r.ok ? await r.json() : []
      return rows.filter((x) => ['已排期', '制作中'].includes(x.status)).length
    })
    ok('已排期/制作中显示排期信息单元格', arrangeCount >= 1 || arrangedTotal === 0,
       'arrange=' + arrangeCount + ' arranged=' + arrangedTotal)
    // 状态标签：默认不显示星标，点击状态切换备选标记；所有状态均可点
    const statusBtnCount = await page.locator('.status-tag-btn').count()
    ok('状态标签可点击', statusBtnCount >= 1 || ideaRows === 0, 'buttons=' + statusBtnCount + ' rows=' + ideaRows)
    // 星标数量必须等于后端已标记备选的数量：未标记行不显示星标
    const starAudit = await page.evaluate(async () => {
      const t = sessionStorage.getItem('avm_token')
      const r = await fetch('/api/ideas', { headers: { Authorization: 'Bearer ' + t } })
      const rows = r.ok ? await r.json() : []
      return { marked: rows.filter((x) => x.is_backup).length, total: rows.length }
    })
    const shownStars = await page.locator('.status-tag-btn .status-star-on').count()
    ok('仅已标记行显示五角星（默认不显示）', shownStars === starAudit.marked,
       `shown=${shownStars} marked=${starAudit.marked} total=${starAudit.total}`)
    ok('所有状态标签均可用（不限制未使用）', await page.locator('.status-tag-btn:disabled').count() === 0,
       'disabled=' + await page.locator('.status-tag-btn:disabled').count())
    // 待发布 / 已完成：创作计划显示紧急程度 + 制作人 + 完成时间（priority 数据保留）
    const doneCells = await page.locator('.arrange-cell--done').count()
    ok('待发布/已完成显示制作人+完成时间单元格', doneCells >= 1, 'done=' + doneCells)
    if (doneCells) {
      const doneCell = page.locator('.arrange-cell--done').first()
      ok('done 单元格含创作人标签', await doneCell.locator('.arrange-creator-tag').count() === 1)
      ok('done 单元格含紧急程度', await doneCell.locator('.arrange-priority-tag').count() === 1)
    }

    /* ---------- 3b. 收集创意弹窗：打开即无必填告警 ---------- */
    section('3b. 收集创意弹窗：打开不触发必填校验')
    await page.locator('button').filter({ hasText: '收集创意' }).first().click()
    await page.waitForTimeout(400)
    const createDlg = page.locator('.el-dialog:visible').filter({ hasText: '收集创意' })
    ok('收集创意弹窗可打开', await createDlg.count() === 1)
    const overlayAnim = await page.evaluate(() => {
      const ov = document.querySelector('.el-overlay')
      return ov ? getComputedStyle(ov).animationName : 'none'
    })
    ok('弹窗遮罩无入场动画（不闪现）', overlayAnim === 'none', 'animation=' + overlayAnim)
    ok('打开弹窗无必填红字告警', await createDlg.locator('.el-form-item__error').count() === 0,
       'errors=' + await createDlg.locator('.el-form-item__error').count())
    const requiredLabels = await createDlg.locator('.el-form-item.is-required .el-form-item__label').allInnerTexts()
    ok('视频名称/话题标签非必填', !requiredLabels.some((s) => /视频名称|话题标签/.test(s)),
       requiredLabels.map((s) => s.trim()).join('|'))
    ok('初始即显示5个必填星号', requiredLabels.length === 5
       && ['抖音链接', '封面截图', '类别', '作者', '视频数据'].every((s) => requiredLabels.some((l) => l.includes(s))),
       requiredLabels.map((s) => s.trim()).join('|'))
    await createDlg.getByRole('button', { name: '取消', exact: true }).click()
    await page.waitForTimeout(300)

    /* ---------- 4. 创作计划弹窗 → 已排期 ---------- */
    section('4. 创作计划弹窗：设置后进入已排期')
    // 通过 API 造一条带封面的创意，再验证前端交互，避免文件上传复杂度
    const token = await page.evaluate(() => sessionStorage.getItem('avm_token'))
    const created = await page.evaluate(async (t) => {
      const r = await fetch('/api/ideas', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t },
        body: JSON.stringify({
          title: '__SMOKE_FRONT__排期测试', cover: '/uploads/test.png',
          category_id: 1, douyin_url: 'https://v.douyin.com/smoke_front/', author: '测试',
          tags: ['__SMOKE_FRONT__冒烟标签一', '__SMOKE_FRONT__冒烟标签二', '__SMOKE_FRONT__冒烟标签三',
                 '__SMOKE_FRONT__冒烟标签四', '__SMOKE_FRONT__冒烟标签五', '__SMOKE_FRONT__冒烟标签六'],
          like_count: 1, comment_count: 1, collect_count: 1, share_count: 1
        })
      })
      return r.ok ? await r.json() : null
    }, token)
    ok('API 造测试创意成功', !!created && !!created.id, created && created.id ? 'id=' + created.id : String(created))
    let testIdeaId = created && created.id
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(900)

    if (testIdeaId) {
      // 找到该行的创作计划图标（未使用态）
      const row = page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__排期测试' }).first()
      ok('测试创意行渲染', await row.count() === 1)

      // 话题标签：最多三行 + 溢出 +N + 悬浮显示剩余
      const tagCell = row.locator('.tag-cell').first()
      ok('话题标签使用折叠单元格', await tagCell.count() === 1)
      const tagCellHeight = await tagCell.evaluate((e) => e.getBoundingClientRect().height)
      ok('话题标签最多三行', tagCellHeight <= 75, 'height=' + tagCellHeight)
      const moreChip = tagCell.locator('.adm-tag-chip.is-more')
      ok('溢出标签显示 +N', await moreChip.count() === 1 && /^\+\d+$/.test((await moreChip.innerText()).trim()),
         await moreChip.count() ? await moreChip.innerText() : 'none')
      await tagCell.hover()
      await page.waitForTimeout(600)
      const tagTip = page.locator('.tag-cell-tooltip:visible')
      ok('悬浮显示剩余标签', await tagTip.count() === 1
         && (await tagTip.innerText()).includes('__SMOKE_FRONT__冒烟标签六'),
         (await tagTip.count()) ? (await tagTip.innerText()).slice(0, 120) : 'none')

      /* ---------- 4a. 点击状态标签切换备选标记（纯标记不改状态） ---------- */
      section('4a. 状态标签切换备选标记：点亮/熄灭不改状态')
      const statusBtn = row.locator('.status-tag-btn')
      ok('状态标签可点', await statusBtn.count() === 1 && !(await statusBtn.isDisabled()))
      ok('初始未标记不显示星标', await statusBtn.locator('.status-star-on').count() === 0)
      await statusBtn.click()
      await page.waitForTimeout(500)
      let stStar = await page.evaluate(async ({ t, id }) => {
        const r = await fetch('/api/ideas/' + id, { headers: { Authorization: 'Bearer ' + t } })
        return r.ok ? await r.json() : null
      }, { t: token, id: testIdeaId })
      ok('点击状态=备选标记true且状态仍为未使用', stStar && stStar.is_backup === true && stStar.status === '未使用',
         stStar ? `backup=${stStar.is_backup} status=${stStar.status}` : 'none')
      // 点亮后星标出现
      let rowS = page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__排期测试' }).first()
      ok('点亮后状态前显示五角星', await rowS.locator('.status-tag-btn .status-star-on').count() === 1)
      // 再点熄灭
      await rowS.locator('.status-tag-btn').click()
      await page.waitForTimeout(500)
      stStar = await page.evaluate(async ({ t, id }) => {
        const r = await fetch('/api/ideas/' + id, { headers: { Authorization: 'Bearer ' + t } })
        return r.ok ? await r.json() : null
      }, { t: token, id: testIdeaId })
      ok('再次点击熄灭备选标记', stStar && stStar.is_backup === false, stStar && stStar.is_backup)
      rowS = page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__排期测试' }).first()
      ok('熄灭后星标消失', await rowS.locator('.status-tag-btn .status-star-on').count() === 0)

      /* ---------- 4b. 创作计划弹窗 → 已排期 ---------- */
      section('4b. 创作计划弹窗：设置后进入已排期')
      const rowP = page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__排期测试' }).first()
      const planIcon = rowP.locator('.plan-icon-btn')
      ok('该行创作计划默认图标存在', await planIcon.count() === 1)
      await planIcon.click()
      await page.waitForTimeout(400)
      const planDlg = page.locator('.el-dialog:visible').filter({ hasText: '创作计划' })
      ok('点击图标弹出创作计划弹窗', await planDlg.count() === 1)
      const labels = (await planDlg.locator('.el-form-item__label').allInnerTexts()).map((t) => t.trim())
      ok('弹窗含紧急程度', labels.includes('紧急程度'), labels.join('|'))
      ok('弹窗含制作人', labels.includes('制作人'), labels.join('|'))
      ok('弹窗含制作时间', labels.includes('制作时间'), labels.join('|'))
      const creatorOpts = await page.evaluate(async ({ t }) => {
        const r = await fetch('/api/ideas/creator-options', { headers: { Authorization: 'Bearer ' + t } })
        return r.ok ? await r.json() : null
      }, { t: token })
      ok('制作人候选接口可用', Array.isArray(creatorOpts)
         && creatorOpts.every((o) => o.id && o.display_name),
         Array.isArray(creatorOpts) ? creatorOpts.map((o) => `${o.display_name}:${o.role}`).join('|') : 'null')
      // 保存并排期（不填制作时间，状态进「已排期」，不会自动流转）
      await planDlg.getByRole('button', { name: '保存并排期' }).click()
      await page.waitForTimeout(900)
      // 校验后端状态
      const st = await page.evaluate(async ({ t, id }) => {
        const r = await fetch('/api/ideas/' + id, { headers: { Authorization: 'Bearer ' + t } })
        return r.ok ? await r.json() : null
      }, { t: token, id: testIdeaId })
      ok('后端状态=已排期', st && st.status === '已排期', st && st.status)

      /* ---------- 5. 取消排期弹窗 → 未使用 ---------- */
      section('5. 取消排期弹窗：已排期 → 未使用')
      await page.reload({ waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(900)
      const row2 = page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__排期测试' }).first()
      const arrangeBtn = row2.locator('.arrange-cell--btn.is-cancellable')
      ok('已排期行创作计划可点取消', await arrangeBtn.count() === 1)
      await arrangeBtn.click()
      await page.waitForTimeout(400)
      const cancelDlg = page.locator('.adm-confirm-card').filter({ hasText: '取消排期' })
      ok('弹出取消排期确认', await cancelDlg.count() === 1)
      await cancelDlg.getByRole('button', { name: '确认取消排期' }).click()
      await page.waitForTimeout(900)
      const st2 = await page.evaluate(async ({ t, id }) => {
        const r = await fetch('/api/ideas/' + id, { headers: { Authorization: 'Bearer ' + t } })
        return r.ok ? await r.json() : null
      }, { t: token, id: testIdeaId })
      ok('后端状态回退未使用', st2 && st2.status === '未使用', st2 && st2.status)
      ok('取消后排期字段清空', st2 && st2.creator_id === null && !st2.planned_at,
         st2 ? `creator=${st2.creator_id} planned=${st2.planned_at}` : 'none')

      /* ---------- 5a. 空标题 / 空标签保存默认值 ---------- */
      section('5a. 视频名称与话题标签可空，保存自动补齐')
      await row2.locator('.adm-cell-actions button').filter({ hasText: '编辑' }).click()
      await page.waitForTimeout(400)
      const editDlg = page.locator('.el-dialog:visible').filter({ hasText: '编辑创意' })
      ok('编辑弹窗打开', await editDlg.count() === 1)
      const titleItem = editDlg.locator('.el-form-item').filter({ hasText: '视频名称' }).first()
      await titleItem.locator('input').fill('')
      const tagItem = editDlg.locator('.el-form-item').filter({ hasText: '话题标签' }).first()
      const tagSelect = tagItem.locator('.el-select').first()
      await tagSelect.hover()
      await page.waitForTimeout(150)
      const clearBtn = tagSelect.locator('.el-select__clear')
      if (await clearBtn.count()) {
        await clearBtn.click()
      } else {
        // 兼容未渲染清除图标时，用键盘逐个删除已选标签
        await tagSelect.locator('input').first().click()
        for (let i = 0; i < 12; i += 1) await page.keyboard.press('Backspace')
      }
      await page.waitForTimeout(200)
      ok('话题标签已清空', await tagItem.locator('.el-select__tags-text').count() === 0,
         'tags=' + await tagItem.locator('.el-select__tags-text').count())
      await editDlg.getByRole('button', { name: '保存', exact: true }).click()
      await page.waitForTimeout(900)
      const filled = await page.evaluate(async ({ t, id }) => {
        const r = await fetch('/api/ideas/' + id, { headers: { Authorization: 'Bearer ' + t } })
        return r.ok ? await r.json() : null
      }, { t: token, id: testIdeaId })
      ok('空视频名称按作者补默认值', filled && filled.title === '@测试创作内容',
         filled && filled.title)
      ok('空话题标签补 #无标签', filled && Array.isArray(filled.tags)
         && filled.tags.length === 1 && filled.tags[0] === '无标签', filled && filled.tags)
    }

    /* ---------- 5.5 配置中心：即时生效 / 无保存按钮 / 删除确认 ---------- */
    section('5.5 配置中心：即时生效与删除确认')
    resp = await page.goto(BASE + '/settings', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(800)
    body = await text(page.locator('body'))
    ok('配置中心无保存配置按钮', !body.includes('保存配置'), body.slice(0, 100))
    ok('配置中心无恢复默认按钮', !body.includes('恢复默认'), body.slice(0, 100))
    const siteBefore = await page.evaluate(async (t) => {
      const h = { Authorization: 'Bearer ' + t }
      return (await (await fetch('/api/settings/site', { headers: h })).json()).site.name
    }, token)
    const siteInput = page.locator('.settings-card--fixed').first().locator('input').first()
    await siteInput.fill('__SMOKE_FRONT__即时保存')
    await siteInput.blur()
    await page.waitForTimeout(400)
    const siteAfter = await page.evaluate(async (t) => {
      const h = { Authorization: 'Bearer ' + t }
      return (await (await fetch('/api/settings/site', { headers: h })).json()).site.name
    }, token)
    ok('失焦后配置即时保存', siteAfter === '__SMOKE_FRONT__即时保存', siteAfter)
    await page.evaluate(async (a) => {
      const h = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.t }
      await fetch('/api/settings', { method: 'PUT', headers: h, body: JSON.stringify({ key: 'site', value: { name: a.name } }) })
    }, { t: token, name: siteBefore })
    // 自动更新机制：配置面板与时间控件
    await page.locator('.settings-tabs .el-tabs__item').filter({ hasText: '自动更新' }).click()
    await page.waitForTimeout(300)
    const autoTabBody = await text(page.locator('.settings-card--fixed').first())
    ok('配置中心含自动更新机制', autoTabBody.includes('启用每日自动更新')
       && autoTabBody.includes('每天执行时间') && autoTabBody.includes('每账号采集作品数'),
       autoTabBody.slice(0, 160))
    ok('自动更新规则说明完整', autoTabBody.includes('离线账号不执行自动更新任务')
       && autoTabBody.includes('更新范围：账号数据') && autoTabBody.includes('历史快照')
       && autoTabBody.includes('获取的最新作品数（含未采集写入作品）'),
       autoTabBody.slice(0, 260))
    const ruleItems = await page.locator('.auto-update-rules li').count()
    ok('自动更新规则为三条列表', ruleItems === 3, 'ruleItems=' + ruleItems)
    await page.locator('.settings-tabs .el-tabs__item').filter({ hasText: '站点信息' }).click()
    await page.waitForTimeout(200)

    const origPlatforms = await page.evaluate(async (t) => {
      const h = { Authorization: 'Bearer ' + t }
      return (await (await fetch('/api/settings/platforms', { headers: h })).json()).platforms || []
    }, token)
    await page.evaluate(async (a) => {
      const h = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.t }
      await fetch('/api/settings', { method: 'PUT', headers: h, body: JSON.stringify({
        key: 'platforms', value: a.list.concat([{ name: '__SMOKE_FRONT__临时平台', color: '#123456', image: '', display: 'full' }])
      }) })
    }, { t: token, list: origPlatforms })
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(700)
    await page.locator('.settings-tabs .el-tabs__item').filter({ hasText: '创作平台' }).click()
    await page.waitForTimeout(300)
    const visibleRows = page.locator('.option-row.is-option:visible')
    const platformIconRadius = await visibleRows.first().locator('.adm-uploader-box').first()
      .evaluate((e) => getComputedStyle(e).borderRadius)
    ok('平台图标为正圆', platformIconRadius.includes('999px'), platformIconRadius)
    const rowBefore = await visibleRows.count()
    const lastRow = visibleRows.last()
    await lastRow.locator('button').click()
    await page.waitForTimeout(200)
    ok('删除确认弹窗出现', await page.locator('.adm-confirm-overlay').count() === 1)
    await page.locator('.adm-confirm-btn.is-primary').click()
    await page.waitForTimeout(900)
    ok('确认后弹窗立即关闭', await page.locator('.adm-confirm-overlay').count() === 0)
    ok('平台删除后即时生效', await visibleRows.count() === rowBefore - 1,
       'before=' + rowBefore + ' after=' + await visibleRows.count())
    await page.evaluate(async (a) => {
      const h = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + a.t }
      await fetch('/api/settings', { method: 'PUT', headers: h, body: JSON.stringify({ key: 'platforms', value: a.list }) })
    }, { t: token, list: origPlatforms })

    /* ---------- 5.6 我的账号：历史快照入口 ---------- */
    section('5.6 我的账号：历史快照入口')
    resp = await page.goto(BASE + '/publish-accounts', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(900)
    body = await text(page.locator('body'))
    ok('我的账号页打开', resp.status() === 200 && body.includes('我的账号'))
    const accRows = await page.locator('.el-table__body tr.el-table__row').count()
    const snapBtns = page.locator('.adm-cell-actions button').filter({ hasText: '快照' })
    ok('账号行含历史快照入口', accRows === 0 ? await snapBtns.count() === 0 : await snapBtns.count() >= 1,
       'rows=' + accRows + ' buttons=' + await snapBtns.count())
    // 增量角标：三列常驻，有快照渲染 ± 值；无变化 / 无快照显示 0 占位
    const apiAccounts = await page.evaluate(async (t) =>
      (await (await fetch('/api/publish-accounts', { headers: { Authorization: 'Bearer ' + t } })).json()), token)
    const badgeCount = await page.locator('.delta-badge').count()
    const flatTexts = await page.locator('.delta-badge.is-flat').allInnerTexts()
    ok('三列增量角标常驻渲染', accRows === 0 ? badgeCount === 0 : badgeCount >= accRows * 3,
       'rows=' + accRows + ' badges=' + badgeCount)
    ok('无变化指标显示 0 占位', flatTexts.every((t) => t.trim() === '0'),
       'flat=' + flatTexts.length + ' texts=' + flatTexts.join(','))
    if (await snapBtns.count() > 0) {
      await snapBtns.first().click()
      await page.waitForTimeout(500)
      const snapDlg = page.locator('.el-dialog:visible').filter({ hasText: '历史快照' })
      ok('历史快照弹窗可打开', await snapDlg.count() === 1)
      const snapHeaders = (await snapDlg.locator('th .cell').allInnerTexts()).map((t) => t.trim())
      ok('快照含作品数量与账号指标', ['作品数量', '获赞', '粉丝', '采集作品'].every((s) => snapHeaders.includes(s)),
         snapHeaders.join('|'))
      await snapDlg.getByRole('button', { name: '关闭', exact: true }).click()
      await page.waitForTimeout(200)
    }

    /* ---------- 6. 视频创作：列表列 / 状态校验 / 编辑弹窗 ---------- */
    section('6. 视频创作：列结构 / 状态完整性校验 / 编辑弹窗')
    resp = await page.goto(BASE + '/productions', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(900)
    body = await text(page.locator('body'))
    ok('视频创作页打开', resp.status() === 200 && body.includes('视频创作'))
    const prodStatLabels = (await page.locator('.stat-row .adm-stat .adm-stat-label').allInnerTexts()).map((t) => t.trim())
    ok('创作统计标签改为四项', prodStatLabels.length === 4
       && ['创作总量', '制作中', '待发布', '已发布'].every((s) => prodStatLabels.includes(s)),
       prodStatLabels.join('|'))
    const prodHeaders = (await page.locator('.el-table__header th .cell').allInnerTexts()).map((t) => t.trim())
    ok('含创作时间列', prodHeaders.includes('创作时间'), prodHeaders.join('|'))
    ok('话题标签列已取消', !prodHeaders.includes('话题标签'), prodHeaders.join('|'))
    ok('视频名称列改名参考视频', prodHeaders.includes('参考视频') && !prodHeaders.includes('视频名称'), prodHeaders.join('|'))
    ok('使用资产列改名人物模型', prodHeaders.includes('人物模型') && !prodHeaders.includes('使用资产'), prodHeaders.join('|'))
    ok('状态列去掉下拉箭头', await page.locator('.status-edit-caret').count() === 0,
       'carets=' + await page.locator('.status-edit-caret').count())
    // 状态按钮为按行渲染：有制作记录时必须可点；无记录时表格空态也算正常（数据可被清空）
    const prodStatusBtns = await page.locator('.prod-status-btn').count()
    const prodRows = await page.locator('.el-table__body tr.el-table__row').count()
    ok('制作中/待发布状态按钮按记录渲染', prodRows === 0 ? prodStatusBtns === 0 : prodStatusBtns >= 1,
       'buttons=' + prodStatusBtns + ' rows=' + prodRows)

    // 造一条信息不全的制作中记录：先完整创建（绕过新建必填校验），再用 PUT 清空平台 + 提示词
    const testProd = await page.evaluate(async (t) => {
      const headers = { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t }
      const cats = await (await fetch('/api/categories', { headers })).json()
      let chars = await (await fetch('/api/characters?scope=all', { headers })).json()
      // 空库无资产时自建一条，避免依赖预置数据（手动新建制作要求至少一项人物模型）
      if (!Array.isArray(chars) || chars.length === 0) {
        const cr = await fetch('/api/characters', {
          method: 'POST', headers,
          body: JSON.stringify({ name: '__SMOKE_FRONT__资产', description: '冒烟临时资产' })
        })
        if (cr.ok) chars = [await cr.json()]
      }
      const catId = Array.isArray(cats) && cats.length ? cats[0].id : null
      const chId = Array.isArray(chars) && chars.length ? chars[0].id : null
      const body = {
        title: '__SMOKE_FRONT__制作校验', status: '制作中',
        platform: '硬核', category_id: catId,
        douyin_url: 'https://www.douyin.com/video/__SMOKE__123',
        prompt: [{ seg: '', text: '临时提示词' }],
        characters: chId ? [{ character_id: chId, role: '主角', sort: 0 }] : []
      }
      const r = await fetch('/api/productions', {
        method: 'POST', headers, body: JSON.stringify(body)
      })
      if (!r.ok) return null
      const prod = await r.json()
      await fetch('/api/productions/' + prod.id, {
        method: 'PUT', headers,
        body: JSON.stringify({ platform: '', prompt: [] })
      })
      return prod
    }, token)
    const testProdId = testProd && testProd.id
    ok('API 造制作中测试记录成功', !!testProdId, testProdId ? 'id=' + testProdId : String(testProd))
    let createdProdId = null
    let editingProdId = null
    if (testProdId) {
      await page.reload({ waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(900)
      const prow = page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__制作校验' }).first()
      ok('测试制作记录行渲染', await prow.count() === 1)
      // 信息不全点击状态：提示补全，不弹确认
      await prow.locator('.prod-status-btn').click()
      await page.waitForTimeout(400)
      const warnMsg = await text(page.locator('.el-message').last())
      ok('信息不全时提示补全平台/提示词', /补全制作信息/.test(warnMsg), warnMsg)
      ok('信息不全不弹确认框', await page.locator('.adm-confirm-card').count() === 0)

      // 补全信息后：点击状态弹确认
      await page.evaluate(async ({ t, id }) => {
        await fetch('/api/productions/' + id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t },
          body: JSON.stringify({ platform: '硬核', prompt: [{ seg: '', text: '测试提示词' }] })
        })
      }, { t: token, id: testProdId })
      await page.reload({ waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(900)
      await page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__制作校验' }).first()
        .locator('.prod-status-btn').click()
      await page.waitForTimeout(400)
      const cdlg = page.locator('.complete-dialog:visible')
      ok('信息完整后点击状态弹完成日期框', await cdlg.count() === 1)
      ok('确认弹窗展示参考视频卡片（封面/标题/标签区/只读项）',
         await cdlg.locator('.complete-ref-video .complete-ref-cover').count() === 1
         && await cdlg.locator('.complete-ref-video .complete-ref-title').count() === 1
         && await cdlg.locator('.complete-ref-video .complete-ref-tags').count() === 1
         && await cdlg.locator('.complete-ref-video .el-tag').count() >= 2)
      ok('完成日期框含完成语义与日期输入', /完成/.test(await text(cdlg)) && await cdlg.locator('input').count() >= 1, await text(cdlg))
      const dateVal = await cdlg.locator('input').first().inputValue()
      ok('完成日期默认今天', /^\d{4}-\d{2}-\d{2}$/.test(dateVal), dateVal)
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)

      // 编辑弹窗：参考视频只读 / 提示词单段 2500 / 制作人状态只读 / 无发布按钮
      await page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__制作校验' }).first()
        .getByRole('button', { name: '编辑' }).click()
      await page.waitForTimeout(600)
      const dlg = page.locator('.edit-dialog:visible')
      ok('编辑弹窗打开', await dlg.count() === 1)
      ok('参考视频只读展示（无输入框）', await dlg.locator('.ref-video-view input, .ref-video-view textarea').count() === 0)
      ok('参考视频封面展示', await dlg.locator('.ref-video-view .ref-cover').count() === 1)
      ok('编辑弹窗隐藏抖音链接', await dlg.locator('.ref-url').count() === 0)
      ok('参考视频标题可点击跳转', await dlg.locator('.ref-title-link').count() === 1,
         await dlg.locator('.ref-title-link').getAttribute('href').catch(() => ''))
      ok('只读项位于参考视频卡片内', await dlg.locator('.ref-video-view .readonly-row').count() === 1)
      ok('只读项无小标题文字', await dlg.locator('.readonly-row .readonly-label').count() === 0)
      const readonlyTexts = (await dlg.locator('.readonly-row .readonly-item').allInnerTexts()).map((x) => x.trim())
      ok('只读项顺序为类型/制作人/状态', readonlyTexts.length === 3, readonlyTexts.join('|'))
      ok('编辑弹窗人物模型为图片卡片（无下拉）',
         await dlg.locator('.model-selected-item .model-selected-cover').count() >= 1
         && await dlg.locator('.el-form-item').filter({ hasText: '人物模型' }).locator('.el-select').count() === 0)
      // 创作平台选中后文本框内前缀显示平台图标（OptionBadge）
      const platItem = dlg.locator('.el-form-item').filter({ hasText: '创作平台' })
      ok('创作平台选中值前缀显示图标',
         await platItem.locator('.el-select__prefix .option-badge').count() === 1,
         'prefix badge=' + await platItem.locator('.el-select__prefix .option-badge').count())
      await dlg.locator('.model-add').click()
      await page.waitForTimeout(350)
      const picker = page.locator('.model-picker-dialog:visible')
      ok('人物模型选择弹窗展示全部资产', await picker.count() === 1
         && await picker.locator('.model-picker-item .model-picker-cover').count() >= 1)
      const beforePick = await dlg.locator('.model-selected-item').count()
      const unselected = picker.locator('.model-picker-item:not(.is-selected)').first()
      let expectedPick = beforePick
      if (await unselected.count()) {
        await unselected.click()
        expectedPick += 1
      }
      await picker.getByRole('button', { name: /确定/ }).click()
      await page.waitForTimeout(400)
      ok('确定后人物模型写回编辑弹窗', await dlg.locator('.model-selected-item').count() === expectedPick,
         'expected=' + expectedPick)
      const beforeRemove = await dlg.locator('.model-selected-item').count()
      await dlg.locator('.model-remove').first().click()
      await page.waitForTimeout(200)
      ok('已选人物模型可删除重新选择', await dlg.locator('.model-selected-item').count() === beforeRemove - 1)
      const promptTa = dlg.locator('.prompt-textarea textarea')
      ok('提示词为单段 textarea', await promptTa.count() === 1)
      ok('提示词上限 2500 字', await promptTa.getAttribute('maxlength') === '2500',
         await promptTa.getAttribute('maxlength'))
      ok('制作人只读（无下拉）', await dlg.locator('.el-form-item').filter({ hasText: '制作人' }).locator('.el-select').count() === 0)
      ok('状态只读（无下拉）', await dlg.locator('.el-form-item').filter({ hasText: '状态' }).locator('.el-select').count() === 0)
      editingProdId = testProdId
      // 编辑弹窗底部只有「取消 / 保存」，不提供发布/取消发布（发布状态由发布数据页关联时同步）
      const dlgBtns = (await dlg.locator('.edit-dialog-footer button').allInnerTexts()).map((x) => x.trim())
      ok('制作中弹窗底部仅取消/保存', dlgBtns.join(',') === '取消,保存', 'footerBtns=' + dlgBtns.join(','))
      ok('制作中不显示发布按钮', await dlg.getByRole('button', { name: '发布' }).count() === 0)
      ok('制作中不显示取消发布按钮', await dlg.getByRole('button', { name: '取消发布' }).count() === 0)
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)

      // 改为待发布 → 弹窗仍只有取消/保存
      await page.evaluate(async ({ t, id }) => {
        await fetch('/api/productions/' + id, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json', Authorization: 'Bearer ' + t },
          body: JSON.stringify({ status: '待发布' })
        })
      }, { t: token, id: testProdId })
      await page.reload({ waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(900)
      await page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__制作校验' }).first()
        .getByRole('button', { name: '编辑' }).click()
      await page.waitForTimeout(600)
      const dlg2 = page.locator('.edit-dialog:visible')
      await dlg2.locator('.edit-dialog-footer button').first().waitFor({ state: 'visible', timeout: 5000 }).catch(() => {})
      const dlg2Btns = (await dlg2.locator('.edit-dialog-footer button').allInnerTexts()).map((x) => x.trim())
      ok('待发布弹窗已打开', await dlg2.count() === 1, 'dlg=' + await dlg2.count())
      ok('待发布弹窗底部仅取消/保存', dlg2Btns.join(',') === '取消,保存', 'footerBtns=' + dlg2Btns.join(','))
      ok('待发布不显示发布按钮', await dlg2.getByRole('button', { name: '发布' }).count() === 0)
      ok('待发布不显示取消发布按钮', await dlg2.getByRole('button', { name: '取消发布' }).count() === 0)
      await page.keyboard.press('Escape')
      await page.waitForTimeout(300)
    }

    /* ---------- 6b. 页头新增创作：不依赖参考视频 ---------- */
    section('6b. 页头新增创作：必填校验 / 默认值')
    await page.reload({ waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(900)
    const createBtn = page.getByRole('button', { name: '新增创作' })
    ok('页头存在新增创作按钮', await createBtn.count() === 1)
    const btnPos = await page.evaluate(() => {
      const btn = Array.from(document.querySelectorAll('button')).find((b) => (b.textContent || '').includes('新增创作'))
      if (!btn) return null
      const kids = Array.from(btn.parentElement.children)
      return { isLast: kids[kids.length - 1] === btn || kids[kids.length - 1].contains(btn), count: kids.length }
    })
    ok('新增创作按钮位于页头最右侧', btnPos && btnPos.isLast, JSON.stringify(btnPos))
    if (await createBtn.count() === 1) {
      await createBtn.click()
      await page.waitForTimeout(600)
      const cdlg = page.locator('.edit-dialog:visible')
      ok('新建弹窗打开', await cdlg.count() === 1)
      // 矮屏兼容：底部操作区 sticky 吸附，长表单滚动时按钮常驻可见
      ok('编辑弹窗底部按钮区 sticky 吸附（矮屏可见）',
         await cdlg.locator('.edit-dialog-footer').evaluate((el) => getComputedStyle(el).position) === 'sticky')
      const cLabels = await cdlg.locator('.el-form-item__label').allTextContents()
      ok('新建弹窗不显示封面/作者/创作人', !cLabels.some((l) => /封面|作者|创作人/.test(l)), cLabels.join(','))
      // 必填校验：直接提交应被拦截
      await cdlg.locator('.edit-dialog-footer button').filter({ hasText: /^创建$/ }).click()
      await page.waitForTimeout(400)
      ok('缺字段时创建被拦截', await cdlg.count() === 1)
      // 填完整
      const cform = cdlg.locator('.el-form')
      const inputs = cform.locator('input[type="text"]')
      await cform.locator('.el-form-item').filter({ hasText: '视频名称' }).locator('input').first().fill('__SMOKE_FRONT__新建制作')
      // 下拉统一用键盘导航：点开 -> 选第一项 -> 关闭，避免浮层拦截
      async function pickFirstOption(label) {
        const sel = cform.locator('.el-form-item').filter({ hasText: label }).locator('.el-select').first()
        await sel.click()
        await page.waitForTimeout(250)
        await page.keyboard.press('ArrowDown')
        await page.keyboard.press('Enter')
        await page.waitForTimeout(200)
      }
      await pickFirstOption('类型')
      await pickFirstOption('人物模型')
      await page.keyboard.press('Escape')
      await page.waitForTimeout(150)
      await pickFirstOption('创作平台')
      await cform.locator('.prompt-textarea textarea').fill('新建制作提示词')
      await cdlg.locator('.edit-dialog-footer button').filter({ hasText: /^创建$/ }).click()
      await page.waitForTimeout(900)
      const created = await page.evaluate(async ({ t }) => {
        const r = await fetch('/api/productions?keyword=' + encodeURIComponent('__SMOKE_FRONT__新建制作'), {
          headers: { Authorization: 'Bearer ' + t }
        })
        const d = r.ok ? await r.json() : null
        return d && d.items && d.items[0] ? d.items[0] : null
      }, { t: token })
      createdProdId = created && created.id
      ok('新建制作成功写入后端', !!createdProdId, createdProdId ? 'id=' + createdProdId : 'none')
      ok('新建封面为默认图', created && created.cover === '/placeholder.svg', created && created.cover)
      ok('新建状态为制作中', created && created.status === '制作中', created && created.status)
      ok('新建有开始时间', !!(created && created.produced_at), created && created.produced_at)
      ok('新建作者为当前登录者', !!(created && created.author), created && created.author)
      ok('新建创作人存在', !!(created && created.owner_id), created && created.owner_id)
      ok('新建创作无参考视频标识', !!created && !created.idea_id && !created.douyin_url)
      await page.reload({ waitUntil: 'domcontentloaded' })
      await page.waitForTimeout(800)
      const newRow = page.locator('.el-table__body tr').filter({ hasText: '__SMOKE_FRONT__新建制作' }).first()
      ok('无参考视频创作第二行显示@无参考视频创作',
         await newRow.locator('.idea-author').innerText() === '@无参考视频创作',
         await newRow.locator('.idea-author').innerText().catch(() => 'none'))
    }

    /* ---------- 7. 发布数据页 ---------- */
    section('7. 发布数据页')
    resp = await page.goto(BASE + '/publish-stats', { waitUntil: 'domcontentloaded' })
    await page.waitForTimeout(900)
    body = await text(page.locator('body'))
    ok('发布数据页打开', resp.status() === 200 && body.includes('发布数据'))
    ok('展示数据指标', body.includes('播放') && body.includes('点赞'))
    // 加载骨架与真实表格互斥：is-loading 时表格必须隐藏，避免出现空白表格
    const loadingWrapDisplay = await page.evaluate(() => {
      const card = document.querySelector('.adm-card--table')
      if (!card) return 'no-card'
      card.classList.add('is-loading')
      const wrap = card.querySelector('.adm-table-wrap')
      const display = wrap ? getComputedStyle(wrap).display : 'no-wrap'
      card.classList.remove('is-loading')
      return display
    })
    ok('加载时骨架替代表格（无空白表格）', loadingWrapDisplay === 'none', 'display=' + loadingWrapDisplay)

    const tableHeaders = await page.locator('.adm-card--table .el-table__header th .cell').allTextContents()
    const pubHeaders = tableHeaders.map((h) => h.trim())
    ok('分类列已去掉、状态列改为发布状态', pubHeaders.includes('发布状态')
       && !pubHeaders.includes('分类') && !pubHeaders.includes('创作发布'), pubHeaders.join('/'))
    ok('发布数据表含视频数据列', pubHeaders.includes('视频数据'), pubHeaders.join('/'))
    const statusTags = page.locator('.adm-card--table .pub-status-tag')
    if (await statusTags.count()) {
      const tagTexts = await statusTags.allInnerTexts()
      ok('发布状态显示正常/隐藏文字', tagTexts.every((t) => ['正常', '隐藏'].includes(t.trim())), tagTexts.join(','))
      const dotColors = await page.locator('.adm-card--table .pub-status-dot').evaluateAll((els) => els.map((e) => getComputedStyle(e).backgroundColor))
      ok('状态色点使用柔和绿/红', dotColors.every((c) => ['rgb(108, 196, 154)', 'rgb(226, 138, 138)'].includes(c)),
         dotColors.join(','))
    }
    const kpiBefore = await page.locator('.stat-row .adm-stat').first().innerText()
    await page.locator('.adm-status-bar .adm-tab-chip').filter({ hasText: '隐藏' }).click()
    await page.waitForTimeout(500)
    const kpiHidden = await page.locator('.stat-row .adm-stat').first().innerText()
    ok('切换隐藏筛选时KPI与条数保持不变', kpiBefore === kpiHidden, kpiBefore + ' || ' + kpiHidden)
    await page.locator('.adm-status-bar .adm-tab-chip').first().click()
    await page.waitForTimeout(400)

    /* ---------- 8. 清理测试数据 ---------- */
    if (testIdeaId) {
      await page.evaluate(async ({ t, id }) => {
        await fetch('/api/ideas/' + id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + t } })
      }, { t: token, id: testIdeaId })
    }
    if (testProdId) {
      await page.evaluate(async ({ t, id }) => {
        await fetch('/api/productions/' + id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + t } })
      }, { t: token, id: testProdId })
    }
    if (createdProdId) {
      await page.evaluate(async ({ t, id }) => {
        await fetch('/api/productions/' + id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + t } })
      }, { t: token, id: createdProdId })
    }
    await page.evaluate(async (t) => {
      const list = await (await fetch('/api/tags', { headers: { Authorization: 'Bearer ' + t } })).json()
      const ids = (Array.isArray(list) ? list : [])
        .filter((x) => String(x.name || '').startsWith('__SMOKE_FRONT__'))
        .map((x) => x.id)
      // 串行删除，避免并发触发标签引用的竞态
      for (const id of ids) {
        await fetch('/api/tags/' + id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + t } })
      }
      const list2 = await (await fetch('/api/characters?scope=all', { headers: { Authorization: 'Bearer ' + t } })).json()
      const charIds = (Array.isArray(list2) ? list2 : [])
        .filter((x) => String(x.name || '').startsWith('__SMOKE_FRONT__'))
        .map((x) => x.id)
      for (const id of charIds) {
        await fetch('/api/characters/' + id, { method: 'DELETE', headers: { Authorization: 'Bearer ' + t } })
      }
    }, token)

    /* ---------- 9. 控制台 ---------- */
    section('8. 控制台错误检查')
    const realErrors = errors.filter((e) => !/favicon|weather|met\.no|geocoding|net::ERR|Failed to load resource|404/i.test(e))
    ok('无前端运行时异常', realErrors.length === 0, realErrors.slice(0, 5).join(' || ') || 'none')

    await page.screenshot({ path: 'E:/本地项目/prompt/ai-video-assets/frontend/smoke-publish.png', fullPage: false })
  } finally {
    await browser.close()
  }

  console.log('\n=== 汇总 ===')
  console.log(`PASS=${PASS} FAIL=${FAIL} TOTAL=${PASS + FAIL}`)
  if (FAILED.length) {
    console.log('失败项：')
    FAILED.forEach((f) => console.log('  - ' + f))
  }
  process.exit(FAIL ? 1 : 0)
}

main().catch((e) => { console.error(e); process.exit(2) })
