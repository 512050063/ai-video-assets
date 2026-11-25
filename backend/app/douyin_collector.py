"""抖音数据采集层（多通道 + 优雅降级）。

背景
----
抖音对网页端有较强的反爬风控：匿名直连 `douyin.com/video/<id>` 与
`aweme/v1/web/...` 系列接口在很多出口 IP 上会被重定向到滑块验证页。
因此这里不假设「一条接口就能打通」，而是准备三条通道，逐级降级：

1. `official`  抖音开放平台（需用户自行申请 app_id / app_secret 并授权）
   —— 最稳定、合规、可定时轮询，优先级最高。
2. `browser`   Playwright 浏览器通道（复用前端已安装的 playwright，
   持久化登录态，用户扫码一次即可）—— 无需企业资质，适合中小账号。
3. `manual`    手工录入兜底 —— 任何通道失败时接口都会返回明确的
   `manual_required` 提示，前端引导用户手填，绝不静默失败。

对外只暴露两个能力：
- `fetch_account(query)`   按抖音号 / sec_uid / 主页链接取账号资料
- `fetch_video(url)`       按作品链接取视频数据（播放/点赞/评论/转发）
"""
import json
import os
import re
import shutil
import ssl
import socket
import subprocess
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Optional

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 抖音短链 / 长链 / 主页链接
VIDEO_ID_PATTERN = re.compile(r"/video/(\d+)")
SEC_UID_PATTERN = re.compile(r"(MS4wLjABAAAA[A-Za-z0-9_\-]+)")
SHORT_CODE_PATTERN = re.compile(r"https?://v\.douyin\.com/([A-Za-z0-9_-]+)/?")
DOYIN_UID_PATTERN = re.compile(r"^[A-Za-z0-9._\-]{3,60}$")

# 浏览器（Playwright）通道的 Node 脚本与登录态目录
_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_COLLECTOR_SCRIPT = os.path.join(_BASE_DIR, "collector", "douyin_collect.mjs")
# 登录态目录可用环境变量覆盖：迁移时若把 data/ 单独挂载，指定 AVM_PROFILE_ROOT 即可
_PROFILE_DIR = os.environ.get("AVM_PROFILE_DIR", "").strip() or os.path.join(
    _BASE_DIR, "data", "douyin_profile")
# 多账号：每个抖音号一个独立持久化登录态目录；未单独登录时回退到公共目录
_PROFILE_ROOT = os.environ.get("AVM_PROFILE_ROOT", "").strip() or os.path.join(
    _BASE_DIR, "data", "douyin_profiles")
# 采集脚本复用前端 node_modules 里的 playwright；迁移可用 AVM_NODE_MODULES 指向独立安装位置
_NODE_MODULES = os.environ.get("AVM_NODE_MODULES", "").strip() or os.path.join(
    os.path.dirname(_BASE_DIR), "frontend", "node_modules")


def _profile_dir(profile_key: str = "", dedicated: bool = False) -> str:
    """把账号标识映射为安全的本地目录；没有独立目录时复用公共登录态。

    dedicated=True 用于首次扫码：直接分配账号专属目录，不回退公共目录。
    """
    key = re.sub(r"[^A-Za-z0-9_-]", "", str(profile_key or ""))[:60]
    if not key:
        return _PROFILE_DIR
    target = os.path.join(_PROFILE_ROOT, key)
    if not dedicated and not os.path.isdir(target):
        return _PROFILE_DIR
    return target


def move_profile(old_key: str, new_key: str) -> None:
    """扫码登录用临时 profile 完成，拿到账号 ID 后把登录态目录改名为账号专属目录。

    目标目录已存在时按文件覆盖合并，不整目录删除：profile 内含大量小文件，
    批量删除会被运行环境的删除守卫拦截并抛 SystemExit，导致扫码接口 500。
    """
    src = _profile_dir(old_key, dedicated=True)
    dst = _profile_dir(new_key, dedicated=True)
    if not os.path.isdir(src) or os.path.abspath(src) == os.path.abspath(dst):
        return
    if os.path.isdir(dst):
        # 目标已存在：逐文件覆盖（新登录态为准），全程不整目录删除，
        # 避免触发运行环境的批量删除守卫。
        try:
            for root, _dirs, files in os.walk(src):
                rel = os.path.relpath(root, src)
                target_dir = dst if rel == "." else os.path.join(dst, rel)
                os.makedirs(target_dir, exist_ok=True)
                for name in files:
                    try:
                        shutil.copy2(os.path.join(root, name), os.path.join(target_dir, name))
                    except Exception:
                        pass
        except Exception:
            pass
    else:
        shutil.move(src, dst)


def new_temp_profile_key() -> str:
    """生成一次性的扫码 profile 标识，登录成功后迁移到账号专属目录。"""
    return f"pending_{int(time.time() * 1000)}"


class CollectError(Exception):
    """采集失败（携带面向用户的中文提示与建议的降级方式）。"""

    def __init__(self, message: str, channel: str = "", manual_hint: str = ""):
        super().__init__(message)
        self.message = message
        self.channel = channel
        self.manual_hint = manual_hint
        self.need_login = False  # 是否需要用户扫码 / 过滑块验证


# ---------------------------------------------------------------- 基础工具
def _http_get(url: str, headers: Optional[dict] = None, timeout: int = 10) -> str:
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(timeout)
    try:
        req = urllib.request.Request(url, headers=headers or {"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
            return resp.read().decode("utf-8", errors="ignore")
    finally:
        socket.setdefaulttimeout(old_timeout)


def expand_short_url(url: str, timeout: int = 8) -> tuple:
    """展开抖音短链，返回 (最终地址, video_id, sec_uid)。"""
    url = (url or "").strip()
    if not url:
        return "", "", ""
    if "v.douyin.com" in url:
        try:
            req = urllib.request.Request(url, headers={"User-Agent": UA})
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE
            with urllib.request.urlopen(req, timeout=timeout, context=ctx) as resp:
                final = resp.geturl()
        except Exception:
            return url, "", ""
    else:
        final = url
    m = VIDEO_ID_PATTERN.search(final)
    vid = m.group(1) if m else ""
    m2 = SEC_UID_PATTERN.search(final)
    sec = m2.group(1) if m2 else ""
    return final, vid, sec


def _extract_douyin_ids(text: str) -> dict:
    """从任意文本里抽取抖音号 / sec_uid / 作品 ID / 主页链接。"""
    out = {"video_id": "", "sec_uid": "", "short_code": "", "url": "", "raw_uid": "", "home_url": ""}
    if not text:
        return out
    text = text.strip()
    m = VIDEO_ID_PATTERN.search(text)
    if m:
        out["video_id"] = m.group(1)
        out["url"] = f"https://www.douyin.com/video/{m.group(1)}"
    m = SEC_UID_PATTERN.search(text)
    if m:
        out["sec_uid"] = m.group(1)
        out["home_url"] = f"https://www.douyin.com/user/{m.group(1)}"
    m = SHORT_CODE_PATTERN.search(text)
    if m:
        out["short_code"] = m.group(1)
        out["url"] = text
    if not out["video_id"] and not out["sec_uid"] and DOYIN_UID_PATTERN.match(text):
        out["raw_uid"] = text
        # 纯抖音号：走搜索页定位账号（浏览器通道用）
        out["url"] = f"https://www.douyin.com/search/{text}?type=user"
    return out


# ------------------------------------------------------- 通道 1：官方开放平台
def _official_config() -> dict:
    """读取官方通道配置（存 system_settings.douyin_official）。"""
    try:
        from .database import SessionLocal
        from .models import SystemSetting

        db = SessionLocal()
        try:
            row = db.query(SystemSetting).filter(SystemSetting.key == "douyin_official").first()
            if not row or not isinstance(row.value, dict):
                return {}
            return dict(row.value)
        finally:
            db.close()
    except Exception:
        return {}


def _official_token(cfg: dict) -> str:
    """取 access_token：优先用配置里手动填的，否则用 client_credentials 换。"""
    token = (cfg.get("access_token") or "").strip()
    if token:
        return token
    app_id = (cfg.get("app_id") or "").strip()
    app_secret = (cfg.get("app_secret") or "").strip()
    if not (app_id and app_secret):
        return ""
    url = "https://open.douyin.com/oauth/access_token/"
    body = urllib.parse.urlencode(
        {
            "client_key": app_id,
            "client_secret": app_secret,
            "grant_type": "client_credentials",
        }
    ).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/x-www-form-urlencoded"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            payload = json.loads(resp.read().decode("utf-8", errors="ignore"))
    except Exception as exc:
        raise CollectError(f"抖音开放平台取 token 失败：{exc}", channel="official")
    data = payload.get("data") or {}
    token = data.get("access_token") or payload.get("access_token") or ""
    if not token:
        raise CollectError(
            f"抖音开放平台未返回 token：{payload.get('description') or payload.get('message') or '未知错误'}",
            channel="official",
        )
    return token


def _official_account(query: dict) -> Optional[dict]:
    """官方通道：拉取用户信息与作品数据。"""
    cfg = _official_config()
    if not cfg:
        return None
    token = _official_token(cfg)
    if not token:
        return None

    headers = {"Authorization": f"Bearer {token}", "User-Agent": UA}
    sec_uid = query.get("sec_uid") or ""
    open_id = (cfg.get("open_id") or "").strip()

    # 1) 作品数据（视频 id 直查）
    if query.get("video_id"):
        url = (
            "https://open.douyin.com/data/v1/item/video_data/?item_id="
            f"{query['video_id']}"
        )
        try:
            payload = json.loads(_http_get(url, headers=headers, timeout=12))
        except Exception:
            payload = {}
        items = (payload.get("data") or {}).get("list") or []
        if items:
            it = items[0]
            return {
                "video_id": query["video_id"],
                "title": it.get("title") or it.get("desc") or "",
                "cover": it.get("cover_url") or "",
                "plays": int(it.get("video_play_count") or 0),
                "likes": int(it.get("video_like_count") or 0),
                "comments": int(it.get("video_comment_count") or 0),
                "shares": int(it.get("video_share_count") or 0),
                "channel": "official",
            }

    # 2) 用户数据（粉丝 / 获赞 / 作品数）
    if open_id:
        url = (
            "https://open.douyin.com/data/v1/user/info/?open_id="
            f"{urllib.parse.quote(open_id)}"
        )
        try:
            payload = json.loads(_http_get(url, headers=headers, timeout=12))
        except Exception:
            payload = {}
        lst = (payload.get("data") or {}).get("list") or []
        if lst:
            u = lst[0]
            return {
                "name": u.get("nickname") or "",
                "avatar": u.get("avatar") or u.get("avatar_url") or "",
                "douyin_uid": u.get("unique_id") or u.get("short_id") or "",
                "sec_uid": sec_uid or u.get("sec_uid") or "",
                "followers_count": int(u.get("follower_count") or 0),
                "likes_count": int(u.get("total_liked") or u.get("likes_count") or 0),
                "video_count": int(u.get("aweme_count") or 0),
                "channel": "official",
            }
    return None


# ------------------------------------------------------ 通道 2：Playwright 浏览器
def _run_browser_collector(
    action: str,
    payload: dict,
    timeout: int = 90,
    headless: bool = True,
    profile_key: str = "",
    dedicated: bool = False,
) -> Optional[dict]:
    """调用 Node Playwright 采集脚本，返回解析后的结果（失败返回 None）。"""
    if not os.path.exists(_COLLECTOR_SCRIPT):
        raise CollectError(
            "浏览器采集组件缺失：未找到 backend/collector/douyin_collect.mjs",
            channel="browser",
            manual_hint="部署包需包含 backend/collector 目录，并确认后端环境变量 AVM_PROFILE_ROOT 等路径配置正确",
        )
    if not os.path.isdir(_NODE_MODULES):
        raise CollectError(
            f"浏览器采集依赖缺失：未找到 Playwright 模块目录 {_NODE_MODULES}",
            channel="browser",
            manual_hint="在部署主机执行 cd frontend && npm install && npx playwright install chromium；或用 AVM_NODE_MODULES 指向已安装 node_modules",
        )
    profile = _profile_dir(profile_key, dedicated=dedicated)
    os.makedirs(profile, exist_ok=True)
    env = dict(os.environ)
    env["NODE_PATH"] = _NODE_MODULES
    env["DOYIN_PROFILE_DIR"] = profile
    env["DOYIN_HEADLESS"] = "0" if not headless else "1"
    try:
        proc = subprocess.run(
            ["node", _COLLECTOR_SCRIPT, action],
            input=json.dumps(payload, ensure_ascii=False),
            capture_output=True,
            text=True,
            timeout=timeout,
            env=env,
            cwd=os.path.dirname(_COLLECTOR_SCRIPT),
        )
    except subprocess.TimeoutExpired:
        raise CollectError("浏览器采集超时，请确认抖音登录态是否有效", channel="browser")
    except Exception as exc:
        raise CollectError(f"浏览器采集启动失败：{exc}", channel="browser")

    out = (proc.stdout or "").strip()
    if not out:
        detail = (proc.stderr or "").strip()[-400:]
        raise CollectError(f"浏览器采集无输出：{detail or '未知错误'}", channel="browser")
    try:
        result = json.loads(out.splitlines()[-1])
    except Exception:
        raise CollectError(f"浏览器采集返回无法解析：{out[:200]}", channel="browser")
    if not result.get("ok"):
        exc = CollectError(
            result.get("message") or "浏览器采集失败",
            channel="browser",
            manual_hint=result.get("manual_hint") or "",
        )
        exc.need_login = bool(result.get("need_login"))
        raise exc
    return result.get("data") or {}


# ------------------------------------------------------------ 对外能力封装
def fetch_account(query: str, channel: str = "auto", profile_key: str = "") -> dict:
    """按抖音号 / sec_uid / 主页链接取账号资料，逐级降级。

    channel: auto（依次降级）/ official（仅官方）/ browser（仅浏览器）
    profile_key: 指定发布账号的独立登录态；为空时用公共登录态。
    """
    raw = (query or "").strip()
    if not raw:
        raise CollectError("请输入抖音号或主页链接", manual_hint="请手工填写账号名称与数据")

    ids = _extract_douyin_ids(raw)
    # 主页短链：先展开拿到 sec_uid
    if ids["short_code"] and not ids["sec_uid"] and not ids["video_id"]:
        final, vid, sec = expand_short_url(ids["url"] or raw)
        ids["sec_uid"] = sec
        ids["video_id"] = vid
        if final:
            ids["url"] = final

    errors = []
    want_official = channel in ("auto", "official")
    want_browser = channel in ("auto", "browser")

    # 1) 官方通道
    if want_official:
        try:
            data = _official_account(ids)
            if data:
                data.setdefault("channel", "official")
                return data
            errors.append("官方通道未配置或无授权数据")
        except CollectError as exc:
            errors.append(f"官方通道：{exc.message}")
        except Exception as exc:
            errors.append(f"官方通道异常：{exc}")
    else:
        errors.append("已跳过官方通道")

    # 2) 浏览器通道
    if want_browser:
        try:
            data = _run_browser_collector(
                "account",
                {
                    "url": ids.get("home_url") or ids.get("url") or raw,
                    "sec_uid": ids.get("sec_uid"),
                    "short_code": ids.get("short_code"),
                    "douyin_uid": ids.get("raw_uid") or "",
                },
                profile_key=profile_key,
            )
            if data:
                data["channel"] = "browser"
                return data
            errors.append("浏览器通道未安装或不可用")
        except CollectError as exc:
            errors.append(f"浏览器通道：{exc.message}")
        except Exception as exc:
            errors.append(f"浏览器通道异常：{exc}")
    else:
        errors.append("已跳过浏览器通道")

    raise CollectError(
        "；".join(errors)[:400] or "抖音账号信息获取失败",
        channel="",
        manual_hint="请手工填写账号名称、视频数量、获赞与粉丝数",
    )


def fetch_account_videos(query: str, limit: int = 10, profile_key: str = "") -> dict:
    """按抖音主页链接 / sec_uid / 抖音号批量取账号作品的播放数据。

    官方开放平台需要用户授权与 open_id，这里统一走浏览器通道；
    失败时返回 need_login 标记，前端引导用户完成抖音验证。
    """
    raw = (query or "").strip()
    if not raw:
        raise CollectError(
            "请输入抖音主页链接或抖音号",
            manual_hint="主页链接形如 https://www.douyin.com/user/MS4wLjABAAAA...",
        )
    ids = _extract_douyin_ids(raw)
    target = ids.get("home_url") or ""
    if not target and ids.get("raw_uid"):
        target = f"https://www.douyin.com/search/{ids['raw_uid']}?type=user"
    if not target:
        raise CollectError("未能识别抖音主页", manual_hint="请填写主页链接或抖音号")

    try:
        data = _run_browser_collector(
            "videos",
            {
                "url": target,
                "sec_uid": ids.get("sec_uid") or "",
                "limit": max(1, min(int(limit or 10), 50)),
            },
            timeout=120,
            profile_key=profile_key,
        )
    except CollectError:
        raise
    except Exception as exc:
        raise CollectError(f"作品列表采集异常：{exc}", channel="browser")
    if not data:
        raise CollectError("浏览器通道未返回作品列表", channel="browser")
    data["channel"] = "browser"
    return data


def fetch_video(url: str, channel: str = "auto", profile_key: str = "") -> dict:
    """按作品链接取视频数据（播放 / 点赞 / 评论 / 转发）。"""
    raw = (url or "").strip()
    if not raw:
        raise CollectError("请输入抖音作品链接", manual_hint="请手工录入本次数据快照")

    ids = _extract_douyin_ids(raw)
    if ids["short_code"] and not ids["video_id"]:
        final, vid, sec = expand_short_url(ids["url"] or raw)
        ids["video_id"] = vid
        ids["sec_uid"] = sec
        if final:
            ids["url"] = final
    if not ids["video_id"]:
        raise CollectError(
            "未能从链接中识别作品 ID",
            manual_hint="请手工录入本次数据快照",
        )

    errors = []
    want_official = channel in ("auto", "official")
    want_browser = channel in ("auto", "browser")

    # 1) 官方通道
    if want_official:
        try:
            data = _official_account(ids)
            if data and "plays" in data:
                data["channel"] = "official"
                return data
            errors.append("官方通道未配置或无授权数据")
        except CollectError as exc:
            errors.append(f"官方通道：{exc.message}")
        except Exception as exc:
            errors.append(f"官方通道异常：{exc}")
    else:
        errors.append("已跳过官方通道")

    # 2) 浏览器通道
    if want_browser:
        try:
            data = _run_browser_collector(
                "video",
                {
                    "url": ids.get("url") or raw,
                    "video_id": ids.get("video_id"),
                    "sec_uid": ids.get("sec_uid"),
                },
                profile_key=profile_key,
            )
            if data:
                data["channel"] = "browser"
                return data
            errors.append("浏览器通道未安装或不可用")
        except CollectError as exc:
            errors.append(f"浏览器通道：{exc.message}")
        except Exception as exc:
            errors.append(f"浏览器通道异常：{exc}")
    else:
        errors.append("已跳过浏览器通道")

    raise CollectError(
        "；".join(errors)[:400] or "视频数据获取失败",
        channel="",
        manual_hint="请手工录入本次数据快照",
    )


def login_douyin(profile_key: str = "") -> dict:
    """打开有头浏览器扫码登录；登录态持久化到该账号专属目录。

    返回当前登录用户信息（尽力而为：昵称 / 抖音号 / sec_uid），
    供调用方回填发布账号资料并记录登录时间。
    """
    result = _run_browser_collector(
        "login",
        {"url": "https://www.douyin.com/", "profile_key": profile_key},
        timeout=180,
        headless=False,
        profile_key=profile_key,
        dedicated=bool(profile_key),
    )
    if not result or not result.get("logged_in"):
        raise CollectError(
            "浏览器未返回有效登录态，已取消建号，请检查部署环境的浏览器依赖",
            channel="browser",
            manual_hint="确认 Node.js/Playwright/Chromium 已安装，且后端进程运行在可打开图形窗口的环境；Linux 无桌面时需配置 Xvfb",
        )
    return result


def now_iso() -> str:
    return datetime.now().isoformat(timespec="seconds")
