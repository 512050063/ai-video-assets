import re
import socket
import ssl
import urllib.error
import urllib.request
from typing import Optional

# 抖音短链码可能包含连字符/下划线（如 edWBkm-meAI），字符集需一并覆盖
URL_PATTERN = re.compile(r"https?://v\.douyin\.com/[A-Za-z0-9_-]+/?")
ANY_URL_PATTERN = re.compile(r"https?://[^\s，,。、）)】\]]+")
CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
TAG_PATTERN = re.compile(r"#\s*([^\s#@]+)")
VIDEO_ID_PATTERN = re.compile(r"/video/(\d+)")

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

# 抖音短链是 302 跳转，跟随后可拿到规范地址与 video id
_EXPAND_TIMEOUT = 6


def _normalize_url(url: str) -> str:
    url = (url or "").strip().rstrip(".,;，；。")
    if url.startswith("//"):
        url = "https:" + url
    return url


def _expand_short_url(url: str) -> tuple:
    """跟随短链跳转，返回 (规范地址, video_id, 是否成功)。

    抖音详情页是 JS 渲染且有反爬，拿不到标题，
    但跳转后的 URL 里带 video id，足以作为稳定标识。
    """
    if "v.douyin.com" not in url:
        vid = ""
        m = VIDEO_ID_PATTERN.search(url)
        if m:
            vid = m.group(1)
        return url, vid, False

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    old_timeout = socket.getdefaulttimeout()
    socket.setdefaulttimeout(_EXPAND_TIMEOUT)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=_EXPAND_TIMEOUT, context=ctx) as resp:
            final_url = resp.geturl()
            try:
                resp.read(1024)
            except Exception:
                pass
        m = VIDEO_ID_PATTERN.search(final_url)
        return final_url, (m.group(1) if m else ""), True
    except Exception:
        return url, "", False
    finally:
        socket.setdefaulttimeout(old_timeout)


def _extract_title(before: str, url: Optional[str]) -> str:
    """取分享口令码之后、链接之前的文案主体。

    规则：
    1. 定位第一个中文字符作为主体起点（口令码 8.74 bnd:/ ... 均为数字/字母/符号）
    2. 剥离尾部的话题标签（#xxx）与 @作者，保持标题干净
    """
    before = before.strip()
    if not before:
        return ""
    cm = CJK_PATTERN.search(before)
    title = before[cm.start():] if cm else before
    title = title.strip(" !！.。:：;；,，、")

    # 剥离尾部的话题标签与 @作者
    title = re.sub(r"#\s*[^\s#@]+\s*", "", title)
    title = re.sub(r"@\S+\s*", "", title)
    title = title.strip(" !！.。:：;；,，、#@")

    # 超长标题截断，避免污染列表展示
    if len(title) > 60:
        title = title[:60].rstrip() + "…"

    return title


def parse_share_text(text: str, expand: bool = False) -> dict:
    """解析抖音分享文案，拆分出链接、视频名称与话题标签。

    示例输入：
      0.00 yGi:/ q@E.UL 05/05 :4pm 让你只属于我的话会不会太自私了？
      # 甜御 # 07 # 氛围 # 双鱼  https://v.douyin.com/me5j6D6mKJs/
      复制此链接，打开Dou音搜索，直接观看视频！

    设计约定：
    1. url 始终保留文案里的原始短链（如 v.douyin.com/xxx），不再替换成
       www.douyin.com/video/数字 长链；短链更短、可直接分享，也更符合用户预期。
    2. 作者不作为解析结果自动回填（分享口令里的 @ 是口令码的一部分，不可靠），
       由用户在表单里手动、非必填填写。
    3. expand 仅用于后台取 video id 做去重，不改变返回给用户的 url。

    说明：抖音详情页为 JS 渲染且有反爬，公开接口也已下线，
    因此标题只能来自分享文案本身；纯链接输入时用短链码生成占位标题。
    """
    raw = (text or "").strip()
    result = {
        "title": "",
        "url": "",
        "raw_url": "",
        "video_id": "",
        "tags": [],
        "author": "",  # 永不自动解析作者，保持手动填写
        "raw": raw,
        "resolved": False,
        "title_from_text": False,
        "message": "",
    }
    if not raw:
        result["message"] = "请输入抖音链接或分享文案"
        return result

    m = URL_PATTERN.search(raw) or ANY_URL_PATTERN.search(raw)
    if not m:
        # 没有链接时，整段当作名称候选
        result["tags"] = TAG_PATTERN.findall(raw)
        result["title"] = _extract_title(raw, None)
        result["title_from_text"] = bool(result["title"])
        result["message"] = "未识别到链接，已按文案生成名称"
        return result

    raw_url = _normalize_url(m.group(0))
    # 核心：无论是否展开，对外 url 都保留原始短链
    result["raw_url"] = raw_url
    result["url"] = raw_url

    before = raw[: m.start()]
    # 话题标签从链接前文案提取；标题剥离话题与 @口令片段后更干净
    result["tags"] = TAG_PATTERN.findall(before)
    result["title"] = _extract_title(before, raw_url)
    result["title_from_text"] = bool(result["title"])

    # 已是长链时，直接从 url 取 video id；短链则按需轻量展开，仅用于去重
    vid_match = VIDEO_ID_PATTERN.search(raw_url)
    if vid_match:
        result["video_id"] = vid_match.group(1)
    elif expand and "v.douyin.com" in raw_url:
        _, video_id, ok = _expand_short_url(raw_url)
        if ok and video_id:
            result["video_id"] = video_id
            result["resolved"] = True
        else:
            result["message"] = "已保留原始短链（未能获取视频 ID，去重可能失效）"

    # 名称兜底：没有文案时用短链码 / video id 生成可读标题
    if not result["title"]:
        code = result["video_id"] or raw_url.rstrip("/").split("/")[-1]
        result["title"] = f"抖音视频 {code}" if code else "未命名抖音视频"
        result["message"] = (
            result["message"]
            or "已保留原始短链，但抖音未开放标题接口，请手动补充视频名称"
        )

    return result
