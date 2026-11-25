# AI 视频创作管理台（Creation Console）

本地部署的短视频资产管理平台：创意收集 → 视频创作 → 数据中心 → 发布账号，配套人物资产、素材共享、角色权限与配置中心。前端 Vue 3 + Element Plus + Vite，后端 FastAPI + SQLAlchemy + SQLite。

## 交付状态

仓库内是**已清空用户业务数据**的可运行基线：

- 仅保留管理员账号 `admin`、系统配置与 5 个上传图标；其余账号、作品、快照、日志、登录态、用户图片均已清除。
- 登录页不再显示默认管理员凭据。
- 发布账号不预置演示数据；首次启动只初始化 5 个默认分类与 3 个默认素材库。
- 干净数据库 `backend/ai_video_assets.db` 随仓库提供；若删除，首次启动会自动重建空库与超管账号。

## 快速启动

### Windows 一键启动

双击根目录 `start.bat`：自动探测 Python/Node、按需安装依赖、释放端口、启动后端与前端并打开浏览器。

- 前端：<http://localhost:5173>
- 后端：<http://127.0.0.1:8000>
- 健康检查：<http://127.0.0.1:8000/api/health>
- 默认管理员：`admin / admin123456`（**登录后立即修改**）

### 手动启动

```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

```bash
cd frontend
npm install
npm run dev
```

生产环境可 `cd frontend && npm run build`，用 Nginx 托管 `frontend/dist` 并将 `/api`、`/uploads` 反代到后端。

## 环境变量

| 变量 | 作用 | 默认值 |
| --- | --- | --- |
| `AVM_SECRET_KEY` | JWT 签名密钥，**生产必设** | 开发默认密钥 |
| `AVM_DB_PATH` | SQLite 绝对路径 | `backend/ai_video_assets.db` |
| `AVM_PROFILE_DIR` | 抖音公共登录态目录 | `backend/data/douyin_profile` |
| `AVM_PROFILE_ROOT` | 多账号登录态根目录 | `backend/data/douyin_profiles` |
| `AVM_NODE_MODULES` | 采集脚本依赖目录 | `frontend/node_modules` |

生产部署还需收紧 `main.py` 中的 CORS 配置，并修改默认管理员密码。

## 验证

```bash
# 后端（需后端服务已启动）
python backend/smoke_test.py
# 前端（Playwright + Chromium）
cd frontend && node smoke_test.cjs
```

2026-11-25 交付验证：后端 **259/259**、前端 **124/124**、Vite 构建通过。测试可通过 `AVM_TEST_DB_PATH` 指向临时库，避免污染交付数据。

## 文档

- `项目文档.md`：功能、接口、配置、迁移部署指南（第 17 章）与交付基线（第 18 章）
- `测试报告.md`：全量功能测试明细（历史记录）
- `start.bat`：Windows 一键启动脚本
