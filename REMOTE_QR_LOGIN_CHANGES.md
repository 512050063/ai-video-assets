# 变更说明：抖音扫码登录远程化 + 服务独立运行

> 本文档可直接作为 GitHub PR 描述或 commit 说明使用。
> 包含两部分：上游提交 `8c3655a` 的权限修复同步，以及本地的远程扫码与服务自启改造。

## 附：本次同步的上游变更（提交 8c3655a）

权限功能修复：`auth.py` 新增 `is_privileged()`（真超管或模块角色 super 均视为超管级别），
`ensure_owner()` 据此放行；抖音配置接口改用 `require_permission(user, "settings.manage", db)`，
不再只认 `is_admin`。同步了 15 个文件（含前端权限 store/路由/Dashboard 与重建的 dist）。
本地远程扫码补丁已与该提交手动合并，两者互不冲突。

## 一、问题背景

原扫码登录流程由后端调用 Playwright，以 `headless=False` 在服务主机上弹出 Chromium 窗口。
当服务部署在局域网服务器时，其他主机通过浏览器点击「抖音扫码登录」，二维码窗口只会出现在
服务器本机桌面，远程用户无法看到，功能不可用。

## 二、解决方案

改为**无头浏览器 + 二维码回传网页**：

1. 后端在无头 Chromium 中打开抖音登录页，抓取二维码元素（抓不到时回退为登录页截图）；
2. 图片以 base64 data URL 通过会话接口回传给前端；
3. 前端弹窗展示二维码，用户用手机抖音扫码；
4. 服务端轮询登录 Cookie，登录成功后把登录态持久化到该账号专属目录，并自动建号/回填资料。

登录态仍保存在磁盘，采集通道行为不变。

## 三、改动文件

| 文件 | 改动内容 |
| --- | --- |
| `backend/collector/douyin_collect.mjs` | 新增 `DOYIN_QR_MODE=1`：输出 `__QR__{...}` 事件行（base64 图片），多选择器定位二维码元素，失败回退整页截图；登录提示文案适配远程扫码。 |
| `backend/app/douyin_collector.py` | `_run_browser_collector()` 支持流式读取 stdout 并回调二维码事件；`login_douyin()` 新增 `qr_mode` / `qr_callback` / `proc_holder` 参数。原有调用路径行为不变。 |
| `backend/app/routers/douyin_collect.py` | 新增远程扫码会话接口与后台工作线程；抽出 `_apply_login_result()` 供同步/异步入口复用。 |
| `frontend/src/views/PublishAccounts.vue` | 新增二维码弹窗、轮询与取消逻辑；「添加账号 → 抖音扫码登录」和账号状态标签改用远程扫码流程。 |
| `frontend/dist/` | 由 `npm run build` 重新生成。 |

## 四、新增 API

### `POST /api/douyin/login/start`

启动扫码会话，立即返回，不阻塞请求。

```json
// 请求：{} 表示新账号；{"account_id": 12} 表示给已有账号重新扫码
{"account_id": 12}

// 响应
{"ok": true, "session": "54387681abd94dbeb513a81136118d2d"}
```

### `GET /api/douyin/login/status?session=<id>&qr_seq=<当前序号>`

轮询扫码状态，需携带登录 Token。`qr` 字段是可直接作为 `img src` 的 data URL；
同一张图片只传一次：客户端带上已收到的 `qr_seq`，图片未变化时 `qr` 返回空字符串。

```json
{
  "ok": false,
  "status": "waiting_scan",
  "qr": "data:image/png;base64,...",
  "qr_seq": 1,
  "kind": "qr",
  "message": "请用手机抖音扫描页面上的二维码",
  "manual_hint": "",
  "need_login": false,
  "result": null
}
```

`status` 取值：`starting` / `waiting_scan` / `success` / `failed` / `cancelled`。
`kind=qr` 表示抓到二维码元素；`kind=page` 表示回退为登录页截图（例如触发风控验证码页）。
`success` 时 `result` 含 `created`、`account_id`、`account_name`、`data`。

### `POST /api/douyin/login/cancel`

```json
{"session": "<id>"}
```

关闭弹窗时调用，终止后台无头浏览器进程并标记会话取消。

### 兼容性

原同步接口 `POST /api/douyin/login` **保留不变**，仍以有头浏览器在服务本机扫码，
供需要在服务器桌面直接操作的场景使用。前端已切换到新的远程扫码流程。

## 五、前端交互变化

- 点击扫码后弹出「抖音扫码登录」窗口，显示二维码或页面截图；
- 提示首次加载约需半分钟（抖音页面在无头浏览器中加载较慢）；
- 扫码成功后弹窗自动关闭，提示建号/回填结果并刷新账号列表；
- 失败时弹窗自动关闭并显示 8 秒提示；
- 用户主动关闭弹窗时调用 cancel 接口清理后台进程。

## 六、验证结果

- 模拟登录页：二维码事件正常输出，PNG 300×300，base64 可解码。
- 端到端：`start → status → cancel` 全部通过；真实抖音页二维码约 28–40 秒回传。
- 重复轮询同一 `qr_seq` 时 `qr` 长度 0，确认图片不会重复传输。
- 健康检查、登录鉴权、新前端 bundle、局域网访问均正常。
- 服务监听 `0.0.0.0:8000`，防火墙规则与开机自启配置未受影响。

## 七、部署与升级说明

- 服务端仍需按部署文档安装 `frontend/node_modules`（Playwright）与 Chromium 内核；
  新流程本身**不需要图形桌面**。
- 前端源码改动后必须执行 `npm run build` 更新 `frontend/dist`。
- 登录态目录 `backend/data/douyin_profiles/` 必须保留，切勿在升级时清理，否则已登录账号需重新扫码。
- 会话状态仅存于内存，服务重启后未完成的扫码会话会丢失，重新点击扫码即可生成新二维码；
  已完成扫码的账号不受影响。

## 八、已知限制

- 抖音页面首次加载较慢，约 30 秒后才出现二维码，前端已有等待提示。
- 服务器出口 IP 若触发抖音风控，页面为验证码中间页，此时回传的是整页截图（`kind=page`）并提示用户，
  无法自动完成滑块验证；需更换出口 IP 或改用手动添加。
- 二维码以 data URL 存于内存并按需传输，避免每次轮询重复发送大图。

## 十、服务独立运行与开机自启（本地部署改造）

原服务在 WorkBuddy 会话内以前台后台任务运行，关闭 WorkBuddy 会导致服务中断。
改为 Windows 计划任务驱动、进程完全脱离 WorkBuddy：

| 文件 | 用途 |
| --- | --- |
| `service_launcher.py` | 以 `DETACHED_PROCESS | CREATE_NO_WINDOW | CREATE_NEW_PROCESS_GROUP` 启动 uvicorn 子进程，输出重定向到 `service.log`，无控制台窗口 |
| `一键隐藏启动.bat` | 双击即用 `pythonw.exe` 隐藏启动服务，并轮询健康检查确认上线 |
| `install-service.ps1` / `安装开机自启.bat` | 注册计划任务「AI Video Assets Service」（AtLogOn、最高权限、失败自动重启 3 次）、配置 TCP 8000 防火墙、移除旧启动文件夹自启项 |
| `uninstall-service.ps1` / `卸载开机自启.bat` | 卸载计划任务与防火墙规则并停止服务 |
| `start-hidden.vbs` / `autostart.vbs` | 兼容旧快捷方式的隐藏启动器 |

关键设计：

- 计划任务使用 `pythonw.exe` 执行 `service_launcher.py`，不产生控制台窗口；
- 子服务进程由启动器以 detached 标志创建，父进程退出后由系统接管，与 WorkBuddy 进程树无关；
- 开机自启触发器为「用户登录时」，登录即自动拉起；服务异常退出由任务计划自动重启。

验证结果：停止 WorkBuddy 内旧服务后，通过计划任务拉起新服务（PID 18188），
父进程链不含 WorkBuddy；localhost / 局域网健康检查、前端页面、新 bundle、
登录与菜单接口、远程扫码会话接口全部正常。

## 建议提交信息

```
feat(douyin): 扫码登录支持局域网远程用户

原流程在有头浏览器中弹窗，远程用户看不到二维码。改为无头浏览器抓取二维码
并通过会话接口回传前端弹窗，手机扫码后登录态仍持久化在服务主机。

- 新增 /api/douyin/login/start、status、cancel 会话接口
- 前端新增二维码弹窗与轮询，成功后自动关闭
- 保留原同步 /login 接口兼容
- 二维码按 qr_seq 只传输一次
```
