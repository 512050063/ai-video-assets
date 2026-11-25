"""AI 视频资产管理系统 - 后端全量冒烟测试

运行：python backend/smoke_test.py
说明：所有测试数据使用 __SMOKE__ 前缀，结束后自动清理，不影响真实业务数据。
"""
import base64
import json
import sqlite3
import sys
import urllib.error
import urllib.request
from datetime import datetime

BASE = "http://127.0.0.1:8000/api"
import os
DB_PATH = os.environ.get(
    "AVM_TEST_DB_PATH",
    r"E:\本地项目\prompt\ai-video-assets\backend\ai_video_assets.db",
)
PREFIX = "__SMOKE__"

PASS = 0
FAIL = 0
DETAILS = []

TOKEN = None
CREATED = {"ideas": [], "categories": [], "characters": [], "productions": [],
           "stats": [], "users": [], "uploads": [], "accounts": [],
           "material_libraries": [], "materials": [], "vote_records": []}


def req(method, path, body=None, token=None, expect=None, raw=False, content_type="application/json"):
    global PASS, FAIL
    import urllib.parse
    url = urllib.parse.quote(BASE + path, safe=":/?&=%")
    data = None
    headers = {}
    if body is not None:
        if raw:
            data = body
        else:
            data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = content_type
    headers["Authorization"] = "Bearer " + (token or TOKEN or "")
    r = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            payload = resp.read()
            code = resp.status
    except urllib.error.HTTPError as e:
        payload = e.read()
        code = e.code
    try:
        parsed = json.loads(payload) if payload else None
    except Exception:
        parsed = payload.decode("utf-8", "ignore")
    return code, parsed


def ok(label, cond, extra=""):
    global PASS, FAIL
    if cond:
        PASS += 1
        DETAILS.append(("PASS", label, extra))
        print("  [PASS] " + label + (" | " + str(extra) if extra else ""))
    else:
        FAIL += 1
        DETAILS.append(("FAIL", label, extra))
        print("  [FAIL] " + label + (" | " + str(extra) if extra else ""))


def section(title):
    print("\n=== " + title + " ===")


def db_count(table):
    c = sqlite3.connect(DB_PATH)
    try:
        return c.execute("SELECT COUNT(*) FROM " + table).fetchone()[0]
    finally:
        c.close()


def cleanup():
    print("\n=== 清理测试数据 ===")
    # 发布账号需先解除与制作记录的关联
    for pid in CREATED.get("productions", []):
        try:
            req("PUT", "/productions/" + str(pid), {"publish_account_id": None})
        except Exception:
            pass
    for rid in reversed(CREATED.get("accounts", [])):
        try:
            code, _ = req("DELETE", "/publish-accounts/" + str(rid))
            print("  DELETE publish-accounts/%s -> %s" % (rid, code))
        except Exception:
            pass
    # 兜底清理冒烟快照，避免历史库外键未开启时留下孤立记录
    try:
        c = sqlite3.connect(DB_PATH)
        try:
            c.execute("DELETE FROM publish_account_snapshots WHERE account_name LIKE ?", (PREFIX + "%",))
            c.commit()
        finally:
            c.close()
    except Exception:
        pass
    # 素材共享：先删素材再删素材库
    for mid in reversed(CREATED.get("materials", [])):
        try:
            req("DELETE", "/material-libraries/materials/" + str(mid))
        except Exception:
            pass
    for lid in reversed(CREATED.get("material_libraries", [])):
        try:
            req("DELETE", "/material-libraries/" + str(lid))
        except Exception:
            pass
    for key in ("stats", "productions", "ideas", "characters", "categories", "users"):
        for rid in reversed(CREATED[key]):
            path = "/" + key + "/" + str(rid)
            code, _ = req("DELETE", path)
            print("  DELETE %s/%s -> %s" % (key, rid, code))
    # 清理冒烟产生的标签
    try:
        code, tags = req("GET", "/tags")
        for t in (tags if isinstance(tags, list) else []):
            if str(t.get("name", "")).startswith(PREFIX):
                req("DELETE", "/tags/" + str(t["id"]))
                print("  DELETE tags/%s -> %s" % (t["id"], t["name"]))
    except Exception:
        pass
    import os
    for p in CREATED["uploads"]:
        try:
            os.remove(p)
            print("  REMOVE " + p)
        except Exception as e:
            print("  REMOVE FAIL " + p + " " + str(e))


def run():
    global TOKEN

    section("1. 基础设施与认证")
    code, data = req("GET", "/health", token="")
    ok("健康检查", code == 200 and data.get("ok") is True, data)

    code, data = req("POST", "/auth/login", {"username": "admin", "password": "wrong-pass"})
    ok("错误密码拒绝登录", code == 400, "code=%s" % code)

    code, data = req("GET", "/ideas", token="invalid-token")
    ok("无效 Token 被拒绝", code == 401, "code=%s" % code)

    code, data = req("GET", "/ideas", token="")
    ok("未登录访问受保护接口被拒绝", code == 401, "code=%s" % code)

    code, data = req("POST", "/auth/login", {"username": "admin", "password": "admin123456"})
    ok("管理员登录", code == 200 and bool(data.get("token")), "role=%s" % data.get("user", {}).get("role"))
    TOKEN = data.get("token")

    code, me = req("GET", "/auth/me")
    ok("获取当前用户", code == 200 and me.get("username") == "admin", me.get("username"))

    code, sess = req("GET", "/auth/sessions")
    ok("会话信息", code == 200 and len(sess) >= 1, sess)

    section("2. 真实数据校验（接口 vs 数据库）")
    tables = {"ideas": "ideas", "categories": "categories", "characters": "characters",
              "productions": "productions", "users": "users"}
    for name, table in tables.items():
        db_n = db_count(table)
        code, rows = req("GET", "/" + name)
        api_n = len(rows) if isinstance(rows, list) else (rows.get("total", -1) if isinstance(rows, dict) else -1)
        ok("%s 数量一致(接口/DB)" % name, code == 200 and api_n == db_n, "api=%s db=%s" % (api_n, db_n))

    code, dash = req("GET", "/dashboard")
    c = sqlite3.connect(DB_PATH)
    scheduled = c.execute(
        "SELECT COUNT(*) FROM ideas WHERE status IN ('已排期','制作中')"
    ).fetchone()[0]
    c.close()
    ok("概览统计来自真实数据", code == 200 and dash.get("schedule_total") == scheduled
       and dash.get("production_total") == db_count("productions")
       and dash.get("character_total") == db_count("characters")
       and dash.get("idea_total") == db_count("ideas"),
       "idea=%s schedule=%s production=%s character=%s" % (dash.get("idea_total"), dash.get("schedule_total"),
                                                            dash.get("production_total"), dash.get("character_total")))
    ok("首页两条主线趋势数据完整", code == 200
       and len(dash.get("schedule_trend") or []) == 14 and len(dash.get("publish_trend") or []) == 14
       and isinstance(dash.get("account_ranking"), list) and isinstance(dash.get("upcoming_ideas"), list),
       "schedule=%s publish=%s accounts=%s" % (len(dash.get("schedule_trend") or []),
                                                len(dash.get("publish_trend") or []),
                                                len(dash.get("account_ranking") or [])))

    section("3. 抖音链接解析")
    share = "8.74 bnd:/ :2pm 测试用视频标题 @测试作者 #测试话题 https://v.douyin.com/abc123/ 复制此链接打开抖音"
    code, parsed = req("POST", "/ideas/parse", {"text": share})
    ok("分享文案解析", code == 200 and "测试用视频标题" in parsed.get("title", "")
       and "测试话题" in parsed.get("tags", []),
       "title=%s tags=%s author=%s" % (parsed.get("title"), parsed.get("tags"), parsed.get("author")))

    # 回归：抖音短链码含连字符/下划线时不能被正则截断
    hyphen_share = "#话题A https://v.douyin.com/edWBkm-meAI/ 复制此链接打开抖音"
    code, parsed_h = req("POST", "/ideas/parse?expand=false", {"text": hyphen_share})
    ok("带连字符短链完整保留", code == 200 and parsed_h.get("url") == "https://v.douyin.com/edWBkm-meAI/",
       "url=%s" % parsed_h.get("url"))

    code, parsed2 = req("POST", "/ideas/parse", {"text": "https://www.douyin.com/video/7123456789012345678"})
    ok("纯链接降级占位标题", code == 200 and bool(parsed2.get("title")) and not parsed2.get("title_from_text"),
       "title=%s msg=%s" % (parsed2.get("title"), parsed2.get("message")))

    code, parsed3 = req("POST", "/ideas/parse", {"text": ""})
    ok("空输入提示", code == 200 and "请输入" in parsed3.get("message", ""), parsed3.get("message"))

    section("4. 分类 CRUD")
    code, cat = req("POST", "/categories", {"name": PREFIX + "分类", "sort": 99})
    ok("新建分类", code == 200 and cat.get("id"), cat.get("name") if isinstance(cat, dict) else cat)
    cat_id = cat.get("id") if isinstance(cat, dict) else None
    if cat_id:
        CREATED["categories"].append(cat_id)
        code, cats = req("GET", "/categories")
        ok("分类列表包含新项", any(x["id"] == cat_id for x in cats))
        code, cat2 = req("PUT", "/categories/%s" % cat_id, {"name": PREFIX + "分类改", "sort": 98})
        ok("修改分类", code == 200 and cat2.get("name") == PREFIX + "分类改", cat2.get("name") if isinstance(cat2, dict) else cat2)

    section("5. 人物资产 CRUD")
    code, ch = req("POST", "/characters", {
        "name": PREFIX + "人物", "description": "测试描述", "tags": ["测试"],
        "images": [{"file_path": "/uploads/test.png", "sort": 0}]})
    ok("新建人物资产", code == 200 and ch.get("id"), ch.get("name") if isinstance(ch, dict) else ch)
    ch_id = ch.get("id") if isinstance(ch, dict) else None
    if ch_id:
        CREATED["characters"].append(ch_id)
        code, chs = req("GET", "/characters")
        ok("人物列表包含新项", any(x["id"] == ch_id for x in chs))
        code, chd = req("GET", "/characters/%s" % ch_id) if False else (200, None)
        code, ch2 = req("PUT", "/characters/%s" % ch_id, {
            "name": PREFIX + "人物改", "description": "改后描述", "tags": ["测试", "改"],
            "images": [{"file_path": "/uploads/test.png", "sort": 0}]})
        ok("修改人物资产", code == 200 and ch2.get("name") == PREFIX + "人物改" and len(ch2.get("images", [])) == 1,
           "images=%s" % len(ch2.get("images", [])) if isinstance(ch2, dict) else ch2)

    section("5.5 创作主线：创意库 → 创作计划 → 视频创作 → 发布数据")
    code, idea = req("POST", "/ideas", {"title": PREFIX + "创意", "tags": ["测试"], "author": PREFIX + "作者"})
    ok("创意库新建（未使用）", code == 200 and idea.get("id") and idea.get("status") == "未使用",
       idea.get("status") if isinstance(idea, dict) else idea)
    idea_id = idea.get("id") if isinstance(idea, dict) else None
    flow_prod_id = None
    if idea_id:
        CREATED["ideas"].append(idea_id)
        # 表格内点击状态标签：仅在「未使用 / 已排期」间互切
        code, st1 = req("PUT", "/ideas/%s/status" % idea_id, {"status": "已排期"})
        ok("状态标签切到已排期", code == 200 and st1.get("status") == "已排期",
           "code=%s status=%s" % (code, st1.get("status") if isinstance(st1, dict) else st1))
        code, st2 = req("PUT", "/ideas/%s/status" % idea_id, {"status": "未使用"})
        ok("状态标签切回未使用", code == 200 and st2.get("status") == "未使用",
           "code=%s status=%s" % (code, st2.get("status") if isinstance(st2, dict) else st2))
        code, st_bad = req("PUT", "/ideas/%s/status" % idea_id, {"status": "制作中"})
        ok("状态标签不能直接切到制作中（须走创作计划）", code == 400, "code=%s" % code)
        # 备选标记：纯标记切换，不改状态
        code, bk1 = req("PUT", "/ideas/%s/backup" % idea_id, {"is_backup": True})
        ok("备选标记点亮", code == 200 and bk1.get("is_backup") is True and bk1.get("status") == "未使用",
           "backup=%s status=%s" % (bk1.get("is_backup"), bk1.get("status")) if isinstance(bk1, dict) else bk1)
        code, bk2 = req("PUT", "/ideas/%s/backup" % idea_id, {"is_backup": False})
        ok("备选标记熄灭", code == 200 and bk2.get("is_backup") is False,
           bk2.get("is_backup") if isinstance(bk2, dict) else bk2)
        # 创作安排接口：制作人候选仅「创作」角色，先准备一个创作角色账号
        arranger_name = PREFIX.lower() + "arranger"
        code, arranger = req("POST", "/users", {"username": arranger_name, "password": "test123456",
                                               "nickname": PREFIX + "制作人", "module_role": "production"})
        arranger_id = arranger.get("id") if isinstance(arranger, dict) else None
        if arranger_id:
            CREATED["users"].append(arranger_id)
        ok("统一角色权限新建创作账号", code == 200 and arranger.get("module_role") == "production"
           and arranger.get("role") == "creator", arranger if isinstance(arranger, dict) else arranger)
        code, opts = req("GET", "/ideas/creator-options")
        ok("制作人候选仅创作角色", code == 200 and isinstance(opts, list) and bool(opts)
           and all(o.get("role") == "creator" for o in opts)
           and arranger_id in [o.get("id") for o in opts], opts)
        creator_id = arranger_id
        code, arr = req("PUT", "/ideas/%s/arrange" % idea_id, {
            "creator_id": creator_id, "priority": 1,
            "planned_at": "2026-12-01T00:00:00"
        })
        ok("创作计划保存后进入已排期", code == 200 and isinstance(arr, dict)
           and arr.get("status") == "已排期" and arr.get("priority") == 1
           and arr.get("creator_id") == creator_id and arr.get("creator_name"),
           "code=%s arr=%s" % (code, {k: arr.get(k) for k in ("status", "priority", "creator_id", "creator_name")} if isinstance(arr, dict) else arr))
        ok("创作计划返回制作时间且排期未到不生成制作记录", isinstance(arr, dict) and bool(arr.get("planned_at"))
           and not arr.get("production_id"),
           "planned_at=%s production_id=%s" % (arr.get("planned_at"), arr.get("production_id")) if isinstance(arr, dict) else arr)
        code, arr_clear = req("PUT", "/ideas/%s/arrange" % idea_id, {"creator_id": None, "planned_at": None})
        ok("创作安排可清空创作人与日期", code == 200 and arr_clear.get("creator_id") is None
           and arr_clear.get("planned_at") is None,
           "creator=%s planned=%s" % (arr_clear.get("creator_id"), arr_clear.get("planned_at")) if isinstance(arr_clear, dict) else arr_clear)
        code, arr_bad = req("PUT", "/ideas/%s/arrange" % idea_id, {"priority": 9})
        ok("创作安排拒绝非法优先级", code == 400, "code=%s" % code)
        code, dup_idea = req("POST", "/ideas", {"title": PREFIX + "创意重复", "video_id": idea.get("video_id") or "X"})
        # 原始创意无 video_id 时去重不生效，dup_idea 会被创建，必须纳入清理避免残留
        if code == 200 and isinstance(dup_idea, dict) and dup_idea.get("id"):
            CREATED["ideas"].append(dup_idea["id"])
        if idea.get("video_id"):
            ok("创意按 video_id 去重", code == 400, "code=%s" % code)
        # 创意点赞投票：一人一票、可取消、票数回退
        code, v1 = req("POST", "/ideas/%s/vote" % idea_id, {})
        ok("创意投票成功", code == 200 and v1.get("votes") == 1 and v1.get("voted") is True,
           "votes=%s voted=%s" % (v1.get("votes"), v1.get("voted")))
        ok("投票人昵称返回", isinstance(v1.get("voter_names"), list) and len(v1["voter_names"]) >= 1,
           v1.get("voter_names"))
        code, v2 = req("POST", "/ideas/%s/vote" % idea_id, {})
        ok("再次点击取消投票（票数归零）", code == 200 and v2.get("votes") == 0 and v2.get("voted") is False,
           "votes=%s voted=%s" % (v2.get("votes"), v2.get("voted")))
        code, v3 = req("POST", "/ideas/%s/vote" % idea_id, {})
        code, v4 = req("POST", "/ideas/%s/vote" % idea_id, {})
        ok("连续切换不重复计票", v3.get("votes") == 1 and v4.get("votes") == 0,
           "v3=%s v4=%s" % (v3.get("votes"), v4.get("votes")))
        code, vlist = req("GET", "/ideas/%s" % idea_id)
        ok("详情接口返回投票字段", "votes" in vlist and "voted" in vlist,
           "votes=%s" % vlist.get("votes"))
        code, v404 = req("POST", "/ideas/999999/vote", {})
        ok("不存在的创意投票返回 404", code == 404, "code=%s" % code)
        code, sch = req("POST", "/ideas/%s/schedule" % idea_id, {"priority": 1, "remark": "排期备注"})
        ok("创意排期只更新创意不生成计划", code == 200 and sch.get("id") == idea_id
           and sch.get("idea_id") == idea_id and sch.get("status") == "已排期", sch)
        code, idea_after = req("GET", "/ideas/%s" % idea_id)
        ok("排期后创意状态=已排期", idea_after.get("status") == "已排期", idea_after.get("status"))
        code, prod = req("POST", "/productions", {
            "title": PREFIX + "主线制作", "category_id": cat_id, "platform": "硬核",
            "prompt": [{"seg": "", "text": "主线提示词"}],
            "status": "制作中", "idea_id": idea_id})
        ok("创意直接创建制作记录", code == 200 and prod.get("id") and prod.get("status") == "制作中", prod)
        flow_prod_id = prod.get("id")
        if flow_prod_id:
            CREATED["productions"].append(flow_prod_id)
            code, fin = req("PUT", "/productions/%s" % flow_prod_id, {"status": "待发布"})
            ok("制作完成进入待发布", code == 200 and fin.get("status") == "待发布", fin.get("status"))
            code, idea_wait = req("GET", "/ideas/%s" % idea_id)
            ok("待发布创意详情返回完成时间", code == 200 and bool(idea_wait.get("completed_at")),
               idea_wait.get("completed_at"))
            code, idea_pre_bk = req("GET", "/ideas/%s" % idea_id)
            pre_bk_status = idea_pre_bk.get("status")
            code, bk_wait = req("PUT", "/ideas/%s/backup" % idea_id, {"is_backup": True})
            ok("非未使用状态也能标记备选且状态不变（不限制状态）",
               code == 200 and bk_wait.get("is_backup") is True and bk_wait.get("status") == pre_bk_status,
               "pre=%s backup=%s status=%s" % (pre_bk_status, bk_wait.get("is_backup"), bk_wait.get("status"))
               if isinstance(bk_wait, dict) else bk_wait)
            req("PUT", "/ideas/%s/backup" % idea_id, {"is_backup": False})
            code, finished = req("GET", "/productions?stage=finished")
            ok("成品页只看待发布/已完成", code == 200 and any(x["id"] == flow_prod_id for x in finished.get("items", [])),
               "total=%s" % finished.get("total"))
            code, making = req("GET", "/productions?stage=making")
            ok("制作页不含成品", code == 200 and not any(x["id"] == flow_prod_id for x in making.get("items", [])))
            code, pub = req("PUT", "/productions/%s" % flow_prod_id, {
                "status": "已完成", "publish_platform": "小红书", "published_url": "https://x.test/v/1"})
            ok("成品发布写入发布平台", code == 200 and pub.get("publish_platform") == "小红书", pub.get("publish_platform"))
            code, stat = req("POST", "/publish-stats", {"production_id": flow_prod_id, "plays": 12, "likes": 3})
            if stat.get("id"):
                CREATED["stats"].append(stat["id"])
            code, summ = req("GET", "/publish-stats/summary")
            fitem = next((x for x in summ.get("items", []) if x["production_id"] == flow_prod_id), None)
            ok("发布数据监视读取发布平台", fitem and fitem.get("publish_platform") == "小红书",
               fitem and fitem.get("publish_platform"))
    code, setg = req("GET", "/settings/publish_platforms")
    ok("配置中心含发布平台", code == 200 and any(p.get("name") == "抖音" for p in setg.get("publish_platforms", [])),
       setg.get("publish_platforms"))

    section("5.6 三菜单流程：5 态主线（去已排期）+ 创作计划 + 创作人/提交人分离")
    code, me_admin = req("GET", "/auth/me")
    admin_id = me_admin.get("id")
    # 创作人用独立用户，提交人保持当前管理员，验证两个字段彻底分开
    cuser = PREFIX.lower() + "creator"
    code, cu = req("POST", "/users", {"username": cuser, "password": "test123456",
                                      "nickname": PREFIX + "创作人", "role": "creator",
                                      "can_create": True, "can_view_all": True})
    main_creator_id = cu.get("id") if isinstance(cu, dict) else None
    if main_creator_id:
        CREATED["users"].append(main_creator_id)
    code, mi = req("POST", "/ideas", {
        "title": PREFIX + "主线创意", "tags": ["主线"], "author": PREFIX + "作者",
        "creator_id": main_creator_id, "priority": 1, "planned_at": "2026-12-01T00:00:00"})
    main_idea_id = mi.get("id") if isinstance(mi, dict) else None
    ok("主线创意创建成功", code == 200 and bool(main_idea_id), mi.get("title") if isinstance(mi, dict) else mi)
    if main_idea_id:
        CREATED["ideas"].append(main_idea_id)
        ok("提交人=当前用户，创作人=独立指定", mi.get("owner_id") == admin_id
           and mi.get("creator_id") == main_creator_id and mi.get("creator_name") == PREFIX + "创作人",
           "owner=%s creator=%s" % (mi.get("owner_name"), mi.get("creator_name")))
        ok("认领机制已废弃（不可认领/不可指定）", mi.get("can_want") is False and mi.get("can_assign") is False,
           "can_want=%s can_assign=%s" % (mi.get("can_want"), mi.get("can_assign")))

        # 状态标签仅在「未使用 / 已排期」间互切
        sc, sr = req("PUT", "/ideas/%s/status" % main_idea_id, {"status": "已排期"})
        ok("状态标签切到已排期", sc == 200 and sr.get("status") == "已排期", sr.get("status"))
        sc, sr = req("PUT", "/ideas/%s/status" % main_idea_id, {"status": "未使用"})
        ok("状态标签切回未使用", sc == 200 and sr.get("status") == "未使用", sr.get("status"))
        # 创作计划弹窗：保存紧急程度/创作人/制作时间 → 进入「已排期」（制作时间未到，不生成制作记录）
        sc, sr = req("PUT", "/ideas/%s/arrange" % main_idea_id, {
            "priority": 1, "creator_id": main_creator_id,
            "planned_at": "2099-12-02T10:30:00"})
        ok("创作计划保存后进入已排期（未来时间不生成制作记录）", sc == 200
           and sr.get("status") == "已排期" and not sr.get("production_id"),
           sr.get("status") if isinstance(sr, dict) else sr)
        # 取消排期：已排期 → 未使用，清空计划字段
        sc, cancel = req("POST", "/ideas/%s/cancel-plan" % main_idea_id)
        ok("取消排期回退到未使用", sc == 200 and cancel.get("status") == "未使用",
           cancel.get("status") if isinstance(cancel, dict) else cancel)
        ok("取消排期清空创作人与制作时间", cancel.get("creator_id") is None
           and cancel.get("planned_at") is None,
           "creator=%s planned=%s" % (cancel.get("creator_id"), cancel.get("planned_at")))
        # 再次排期，制作时间设为过去 → 惰性查询触发自动流转到制作中并生成制作记录
        sc, sr2 = req("PUT", "/ideas/%s/arrange" % main_idea_id, {
            "priority": 2, "creator_id": main_creator_id,
            "planned_at": "2020-01-03T09:00:00"})
        ok("排期时间设为过去仍先记已排期", sc == 200 and sr2.get("status") == "已排期",
           sr2.get("status") if isinstance(sr2, dict) else sr2)
        code, making_detail = req("GET", "/ideas/%s" % main_idea_id)
        main_prod_id = making_detail.get("production_id")
        ok("排期时间到自动流转到制作中并生成唯一制作记录",
           making_detail.get("status") == "制作中" and bool(main_prod_id),
           "status=%s prod=%s" % (making_detail.get("status"), main_prod_id))
        if main_prod_id:
            CREATED["productions"].append(main_prod_id)
            code, mprod = req("GET", "/productions/%s" % main_prod_id)
            ok("制作记录关联来源创意与创作人", mprod.get("idea_id") == main_idea_id
               and mprod.get("owner_id") == main_creator_id,
               "idea=%s owner=%s" % (mprod.get("idea_id"), mprod.get("owner_id")))
            ok("开始时间取排期时间 planned_at", mprod.get("produced_at") is not None
               and "T09:00:00" in str(mprod.get("produced_at")), mprod.get("produced_at"))
        # 视频创作页：制作中 → 待发布 →（还原）制作中 → 待发布
        sc, wait1 = req("PUT", "/productions/%s" % main_prod_id, {"status": "待发布"})
        ok("视频创作确认完成进入待发布", sc == 200 and wait1.get("status") == "待发布",
           wait1.get("status") if isinstance(wait1, dict) else wait1)
        code, waiting = req("GET", "/productions/%s" % main_prod_id)
        ok("待发布写入完成时间", bool(waiting.get("completed_at")), waiting.get("completed_at"))
        sc, back = req("PUT", "/productions/%s" % main_prod_id, {"status": "制作中"})
        ok("待发布确认还原为制作中", sc == 200 and back.get("status") == "制作中"
           and back.get("completed_at") is None,
           back.get("status") if isinstance(back, dict) else back)
        req("PUT", "/productions/%s" % main_prod_id, {"status": "待发布"})
        # 发布数据录入：自动推进到已完成（不再手动点完成）
        code, mstat = req("POST", "/publish-stats", {"production_id": main_prod_id,
                                                     "plays": 66, "likes": 6, "comments": 2, "shares": 1})
        if mstat.get("id"):
            CREATED["stats"].append(mstat["id"])
        code, done_idea = req("GET", "/ideas/%s" % main_idea_id)
        code, done_prod = req("GET", "/productions/%s" % main_prod_id)
        ok("录入发布数据后创意与制作记录推进到已完成", done_idea.get("status") == "已完成"
           and done_prod.get("status") == "已完成",
           "idea=%s prod=%s" % (done_idea.get("status"), done_prod.get("status")))
        ok("已完成写入发布时间", bool(done_prod.get("published_at")), done_prod.get("published_at"))
        # 数据状态独立于流程状态
        ok("数据状态独立于流程状态（默认正常）", done_prod.get("data_status") == "正常"
           and done_idea.get("status") == "已完成", done_prod.get("data_status"))
        # 已完成创意在灵感页状态标签只读，不接受直接改状态
        sc, sr = req("PUT", "/ideas/%s/status" % main_idea_id, {"status": "未使用"})
        ok("已完成创意不接受状态标签直接回退", sc == 400, "code=%s" % sc)

    section("6. 已下线模块与创意统计字段")
    code, _ = req("GET", "/plans")
    ok("排期计划接口已下线", code == 404, "code=%s" % code)
    code, _ = req("GET", "/finished")
    ok("视频发布接口已下线", code == 404, "code=%s" % code)
    vid = "998877665544332211"
    code, first_idea = req("POST", "/ideas", {
        "title": PREFIX + "去重原始", "video_id": vid, "author": PREFIX + "作者", "tags": ["测试"]})
    if code == 200 and isinstance(first_idea, dict) and first_idea.get("id"):
        CREATED["ideas"].append(first_idea["id"])
    code, dup_idea = req("POST", "/ideas", {
        "title": PREFIX + "去重创意", "video_id": vid, "author": PREFIX + "作者", "tags": ["测试"]})
    ok("创意按 video_id 去重生效", code == 400 and "已存在" in str(dup_idea.get("detail", "")), "code=%s" % code)
    code, stat_rows = req("GET", "/ideas")
    ok("创意列表提供统计与标签筛选字段", code == 200 and isinstance(stat_rows, list)
       and all(all(k in r for k in ("status", "is_backup", "created_at")) for r in stat_rows),
       "rows=%s" % len(stat_rows) if isinstance(stat_rows, list) else stat_rows)

    section("7. 视频制作 CRUD / 状态机 / 人物绑定")
    # 手动新建（不依赖参考视频）：必填校验 + 作者/创作人/开始时间兜底
    code, bad_prod = req("POST", "/productions", {"title": PREFIX + "残缺制作"})
    ok("手动新建缺必填被拒", code == 400 and "类型" in str(bad_prod.get("detail", "")),
       "%s %s" % (code, bad_prod.get("detail") if isinstance(bad_prod, dict) else bad_prod))
    code, manual = req("POST", "/productions", {
        "title": PREFIX + "手动新建", "cover": "/placeholder.svg",
        "category_id": cat_id, "platform": "硬核",
        "prompt": [{"seg": "", "text": "手动提示词"}],
        "characters": [{"character_id": ch_id, "role": "主角", "sort": 0}] if ch_id else [],
    })
    ok("手动新建制作成功", code == 200 and bool(manual.get("id")),
       manual.get("title") if isinstance(manual, dict) else manual)
    manual_id = manual.get("id") if isinstance(manual, dict) else None
    if manual_id:
        CREATED["productions"].append(manual_id)
        ok("手动新建默认封面", manual.get("cover") == "/placeholder.svg", manual.get("cover"))
        code, me = req("GET", "/auth/me")
        my_name = (me.get("nickname") or me.get("username")) if isinstance(me, dict) else ""
        ok("手动新建作者=当前登录者", manual.get("author") == my_name and bool(my_name),
           "author=%s me=%s" % (manual.get("author"), my_name))
        ok("手动新建创作人=当前登录者", bool(manual.get("owner_id")), manual.get("owner_id"))
        ok("手动新建开始时间=提交时间", bool(manual.get("produced_at")), manual.get("produced_at"))
        ok("手动新建无来源创意", manual.get("idea_id") is None, manual.get("idea_id"))

    code, prod = req("POST", "/productions", {
        "title": PREFIX + "制作", "category_id": cat_id,
        "platform": "硬核", "status": "制作中",
        "prompt": [{"seg": "人物背景", "text": "测试提示词"}],
        "reference_url": "https://example.com/ref", "duration": 15.5,
        "characters": [{"character_id": ch_id, "role": "主角", "sort": 0}] if ch_id else [],
        "assets": [{"type": "cover", "file_path": "/uploads/cover.png", "sort": 0}]})
    ok("新建制作", code == 200 and prod.get("id"), prod.get("title") if isinstance(prod, dict) else prod)
    prod_id = prod.get("id") if isinstance(prod, dict) else None
    if prod_id:
        CREATED["productions"].append(prod_id)
        ok("进入制作中自动写 produced_at", bool(prod.get("produced_at")), prod.get("produced_at"))
        ok("人物绑定成功", len(prod.get("characters", [])) == 1 and prod["characters"][0]["character_name"] == PREFIX + "人物改",
           prod.get("characters"))
        ok("提示词保存", len(prod.get("prompt", [])) == 1 and prod["prompt"][0]["text"] == "测试提示词")
        ok("附件保存", len(prod.get("assets", [])) == 1 and prod["assets"][0]["type"] == "cover")
        code, pd = req("GET", "/productions/%s" % prod_id)
        ok("制作详情接口正常", code == 200 and pd.get("id") == prod_id, pd.get("id"))

        code, p_done = req("PUT", "/productions/%s" % prod_id, {"status": "待发布"})
        ok("状态流转到待发布并写 completed_at", code == 200 and p_done.get("status") == "待发布" and bool(p_done.get("completed_at")),
           p_done.get("completed_at") if isinstance(p_done, dict) else p_done)
        ok("部分更新未清空人物绑定", len(p_done.get("characters", [])) == 1)
        ok("部分更新未清空提示词", len(p_done.get("prompt", [])) == 1)

        code, p_pub = req("PUT", "/productions/%s" % prod_id, {"status": "已完成", "published_url": "https://www.douyin.com/video/9988"})
        ok("状态流转到已完成并写 published_at", code == 200 and bool(p_pub.get("published_at")), p_pub.get("published_at"))

        code, p_back = req("PUT", "/productions/%s" % prod_id, {"status": "制作中"})
        ok("状态回退清空完成/发布时间", code == 200 and p_back.get("completed_at") is None and p_back.get("published_at") is None,
           "completed=%s published=%s" % (p_back.get("completed_at"), p_back.get("published_at")))

        code, filtered = req("GET", "/productions?status=制作中&platform=硬核")
        ok("制作多条件筛选", code == 200 and any(x["id"] == prod_id for x in filtered.get("items", [])),
           "total=%s" % filtered.get("total"))

    section("8. 发布数据 CRUD 与汇总")
    if prod_id:
        code, s1 = req("POST", "/publish-stats", {"production_id": prod_id, "plays": 100, "likes": 10, "comments": 5, "shares": 2,
                                                  "recorded_at": "2026-01-15T10:00:00"})
        ok("录入第一条数据", code == 200 and s1.get("id"), s1)
        s1_id = s1.get("id") if isinstance(s1, dict) else None
        if s1_id:
            CREATED["stats"].append(s1_id)

        # 采集数据按 video_id 去重：同一作品重复写入只更新原快照
        vid = PREFIX.lower() + "-video-001"
        code, dup = req("POST", "/publish-stats", {"production_id": prod_id, "plays": 120, "likes": 12, "comments": 6, "shares": 3,
                                                   "video_id": vid, "source": "auto", "recorded_at": "2026-02-15T10:00:00"})
        ok("采集写入带 video_id", code == 200 and dup.get("video_id") == vid, dup)
        dup_id = dup.get("id") if isinstance(dup, dict) else None
        code, dup2 = req("POST", "/publish-stats", {"production_id": prod_id, "plays": 125, "likes": 13, "comments": 7, "shares": 4,
                                                    "video_id": vid, "source": "auto", "recorded_at": "2026-02-15T11:00:00"})
        ok("同作品去重（更新不新增）", code == 200 and dup2.get("id") == dup_id and dup2.get("plays") == 125, dup2)

        # 手工录入不带 video_id，保留按时间留痕的历史快照
        code, s2 = req("POST", "/publish-stats", {"production_id": prod_id, "plays": 300, "likes": 30, "comments": 15, "shares": 6})
        ok("录入第二条数据（手工留痕）", code == 200 and s2.get("id"), s2)
        s2_id = s2.get("id") if isinstance(s2, dict) else None
        if s2_id:
            CREATED["stats"].append(s2_id)
        if dup_id:
            CREATED["stats"].append(dup_id)
        code, stats = req("GET", "/publish-stats?production_id=%s" % prod_id)
        ok("数据快照列表（去重后 3 条）", code == 200 and len(stats) == 3, "count=%s" % len(stats))

        code, pub = req("PUT", "/productions/%s" % prod_id, {"status": "已完成"})
        code, summary = req("GET", "/publish-stats/summary")
        item = next((x for x in summary.get("items", []) if x["production_id"] == prod_id), None)
        ok("汇总取最新快照", item is not None and item.get("plays") == 300, "plays=%s" % (item or {}).get("plays"))
        ok("汇总统计合计", summary.get("total", {}).get("plays", 0) >= 300, summary.get("total"))
        ok("汇总项带 stat_id（供前端定位快照）",
           item is not None and item.get("stat_id") == s2_id,
           "stat_id=%s expect=%s" % ((item or {}).get("stat_id"), s2_id))

        # 快照编辑：只更新显式传入的字段
        if s2_id:
            code, upd = req("PUT", "/publish-stats/%s" % s2_id, {"plays": 555, "likes": 66})
            ok("编辑快照（部分更新）",
               code == 200 and upd.get("plays") == 555 and upd.get("likes") == 66,
               "plays=%s likes=%s" % ((upd or {}).get("plays"), (upd or {}).get("likes")))
            code, after = req("GET", "/publish-stats?production_id=%s" % prod_id)
            cur = next((x for x in after if x["id"] == s2_id), None)
            ok("快照编辑保留未传字段（评论/转发）",
               cur is not None and cur.get("comments") == 15 and cur.get("shares") == 6, cur)
            code, _ = req("PUT", "/publish-stats/%s" % s2_id, {"plays": -5})
            cur2 = next((x for x in req("GET", "/publish-stats?production_id=%s" % prod_id)[1] if x["id"] == s2_id), None)
            ok("快照编辑负值归零", cur2 is not None and cur2.get("plays") == 0, cur2)
            req("PUT", "/publish-stats/%s" % s2_id, {"plays": 300})

        code, _ = req("PUT", "/publish-stats/99999999", {"plays": 1})
        ok("编辑不存在的快照返回 404", code == 404, "code=%s" % code)

        if s1_id:
            code, _ = req("DELETE", "/publish-stats/%s" % s1_id)
            ok("删除单条数据", code == 200)
            CREATED["stats"].remove(s1_id)

    section("9. 用户管理与权限")
    uname = PREFIX.lower() + "viewer"
    code, vu = req("POST", "/users", {"username": uname, "password": "test123456",
                                     "nickname": "测试只读", "role": "viewer", "can_create": False, "can_view_all": True})
    ok("管理员新建只读用户", code == 200 and vu.get("role") == "viewer", vu.get("username") if isinstance(vu, dict) else vu)
    vu_id = vu.get("id") if isinstance(vu, dict) else None
    if vu_id:
        CREATED["users"].append(vu_id)
        code, vlogin = req("POST", "/auth/login", {"username": uname, "password": "test123456"})
        ok("新用户登录", code == 200 and bool(vlogin.get("token")), "code=%s" % code)
        vtoken = vlogin.get("token") if isinstance(vlogin, dict) else None
        code, videas = req("GET", "/ideas", token=vtoken)
        ok("只读用户可查看创意", code == 200, "count=%s" % len(videas) if isinstance(videas, list) else videas)
        code, vcreate = req("POST", "/ideas", {"title": PREFIX + "越权"}, token=vtoken)
        ok("只读用户创建被拒绝", code == 403, "code=%s" % code)
        code, vusers = req("GET", "/users", token=vtoken)
        ok("非管理员访问用户管理被拒绝", code == 403, "code=%s" % code)
        code, vupd = req("PUT", "/users/%s" % vu_id, {"role": "creator", "nickname": "测试创作者"})
        ok("管理员修改用户角色", code == 200 and vupd.get("role") == "creator", vupd.get("role") if isinstance(vupd, dict) else vupd)
        code, vreset = req("POST", "/users/%s/reset-password" % vu_id, {"new_password": "new123456"})
        ok("管理员重置密码", code == 200)
        code, vlogin2 = req("POST", "/auth/login", {"username": uname, "password": "new123456"})
        ok("新密码可登录", code == 200 and bool(vlogin2.get("token")), "code=%s" % code)
        code, vdis = req("PUT", "/users/%s" % vu_id, {"is_active": False})
        ok("管理员停用用户", code == 200 and vdis.get("is_active") is False, vdis.get("is_active") if isinstance(vdis, dict) else vdis)
        code, vlogin3 = req("POST", "/auth/login", {"username": uname, "password": "new123456"})
        ok("停用账号无法登录", code == 403, "code=%s" % code)
        code, selfdel = req("DELETE", "/users/1")
        ok("禁止删除当前登录账号", code == 400, "code=%s" % code)

    section("10. 配置中心")
    code, settings = req("GET", "/settings")
    ok("读取全部配置", code == 200 and all(k in settings for k in
       ["site", "defaults", "prompt", "douyin", "auto_update", "security", "welcome"]), list(settings.keys()))
    code, auto_cfg = req("GET", "/settings/auto_update")
    au = auto_cfg.get("auto_update", {}) if isinstance(auto_cfg, dict) else {}
    ok("自动更新配置含每日时间", code == 200 and all(k in au for k in
       ["enabled", "hour", "minute", "video_limit", "sync_publish_data"]), au)
    old_au = dict(au)
    code, au_upd = req("PUT", "/settings", {"key": "auto_update", "value": {
        "enabled": False, "hour": 9, "minute": 30, "video_limit": 5, "sync_publish_data": False}})
    ok("自动更新配置可即时保存", code == 200 and au_upd.get("value", {}).get("hour") == 9
       and au_upd.get("value", {}).get("minute") == 30, au_upd.get("value") if isinstance(au_upd, dict) else au_upd)
    code, au_bad = req("PUT", "/settings", {"key": "auto_update", "value": {
        "hour": 99, "minute": 99, "video_limit": 999}})
    bad_val = au_bad.get("value", {}) if isinstance(au_bad, dict) else {}
    ok("自动更新时间非法值被归一化", code == 200 and bad_val.get("hour") == 8
       and bad_val.get("minute") == 0 and bad_val.get("video_limit") == 20, bad_val)
    req("PUT", "/settings", {"key": "auto_update", "value": old_au})
    code, welcome = req("GET", "/settings/welcome")
    ok("读取单项配置", code == 200 and "city" in welcome.get("welcome", {}), welcome)
    code, badkey = req("GET", "/settings/__not_exist__")
    ok("未知配置项 404", code == 404, "code=%s" % code)
    code, supd = req("PUT", "/settings", {"key": "welcome", "value": {"city": "测试市"}})
    ok("管理员修改配置", code == 200)
    code, wcheck = req("GET", "/settings/welcome")
    ok("配置修改已持久化", wcheck.get("welcome", {}).get("city") == "测试市", wcheck.get("welcome"))
    req("PUT", "/settings", {"key": "welcome", "value": {"city": welcome.get("welcome", {}).get("city", "深圳"),
        "latitude": welcome.get("welcome", {}).get("latitude"),
        "longitude": welcome.get("welcome", {}).get("longitude")}})
    if vu_id:
        vtoken = None
        code, vl = req("POST", "/auth/login", {"username": uname, "password": "new123456"})
        if code != 200:
            req("PUT", "/users/%s" % vu_id, {"is_active": True})
            code, vl = req("POST", "/auth/login", {"username": uname, "password": "new123456"})
        vtoken = vl.get("token") if isinstance(vl, dict) else None
        code, vset = req("PUT", "/settings", {"key": "site", "value": {"name": "越权"}}, token=vtoken)
        ok("非管理员修改配置被拒绝", code == 403, "code=%s" % code)

    section("11. 文件上传与静态访问")
    png = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8z8DwHwAFAAH/q842iQAAAABJRU5ErkJggg==")
    boundary = "----smokeboundary"
    body = (("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"smoke.png\"\r\n"
             "Content-Type: image/png\r\n\r\n" % boundary).encode() + png + ("\r\n--%s--\r\n" % boundary).encode())
    code, up = req("POST", "/upload", body, raw=True, content_type="multipart/form-data; boundary=" + boundary)
    ok("上传图片", code == 200 and up.get("url", "").startswith("/uploads/"), up.get("url") if isinstance(up, dict) else up)
    if isinstance(up, dict) and up.get("url"):
        import os
        fp = r"E:\本地项目\prompt\ai-video-assets\backend" + up["url"].replace("/uploads/", "/uploads/")
        CREATED["uploads"].append(fp)
        try:
            with urllib.request.urlopen("http://127.0.0.1:8000" + up["url"], timeout=10) as resp:
                ok("上传文件可静态访问", resp.status == 200 and resp.read() == png)
        except Exception as e:
            ok("上传文件可静态访问", False, str(e))
    bad = (("--%s\r\nContent-Disposition: form-data; name=\"file\"; filename=\"bad.exe\"\r\n"
            "Content-Type: application/octet-stream\r\n\r\n" % boundary).encode() + b"x" + ("\r\n--%s--\r\n" % boundary).encode())
    code, _ = req("POST", "/upload", bad, raw=True, content_type="multipart/form-data; boundary=" + boundary)
    ok("拒绝非法文件类型", code == 400, "code=%s" % code)

    section("12. 个人中心")
    code, prof = req("PUT", "/auth/profile", {"nickname": PREFIX + "昵称", "phone": "13800000000", "email": "smoke@test.com"})
    ok("修改个人资料", code == 200 and prof.get("phone") == "13800000000", prof.get("nickname") if isinstance(prof, dict) else prof)
    req("PUT", "/auth/profile", {"nickname": "超级管理员", "phone": "", "email": ""})
    code, av = req("PUT", "/auth/avatar", {"avatar": "/uploads/test-avatar.png"})
    ok("修改头像", code == 200 and "test-avatar" in av.get("avatar", ""), av.get("avatar") if isinstance(av, dict) else av)
    req("PUT", "/auth/avatar", {"avatar": ""})
    code, pw = req("POST", "/auth/password", {"old_password": "wrong", "new_password": "abcdef123"})
    ok("改密码校验原密码", code == 400, "code=%s" % code)

    section("13. 标签库：自动登记 / 引用计数 / 去重")
    tag_name = PREFIX + "标签"
    code, idea_tag = req("POST", "/ideas", {
        "title": PREFIX + "标签创意", "tags": [tag_name, PREFIX + "标签2"],
        "douyin_url": "https://v.douyin.com/smoke_tag_001/"})
    ok("新建创意带标签", code == 200 and idea_tag.get("id"), idea_tag.get("title") if isinstance(idea_tag, dict) else idea_tag)
    idea_tag_id = idea_tag.get("id") if isinstance(idea_tag, dict) else None
    if idea_tag_id:
        CREATED["ideas"].append(idea_tag_id)
    code, tag_list = req("GET", "/tags")
    names = [t["name"] for t in tag_list] if isinstance(tag_list, list) else []
    ok("标签自动登记到标签库", tag_name in names, names[:8])
    code, tag_opts = req("GET", "/tags/options")
    ok("标签下拉数据可读", code == 200 and any(o["name"] == tag_name for o in tag_opts),
       "count=%s" % (len(tag_opts) if isinstance(tag_opts, list) else 0))
    code, dup_tag = req("POST", "/tags", {"name": tag_name})
    ok("同名标签不允许重复创建", code == 400, "code=%s" % code)
    code, new_tag = req("POST", "/tags", {"name": PREFIX + "手工标签", "category": "风格"})
    ok("手工新建标签", code == 200 and new_tag.get("name") == PREFIX + "手工标签", new_tag)
    manual_tag_id = new_tag.get("id") if isinstance(new_tag, dict) else None
    if manual_tag_id:
        code, _ = req("DELETE", "/tags/%s" % manual_tag_id)
        ok("删除标签", code == 200, "code=%s" % code)
    code, tag_sync = req("POST", "/tags/sync")
    ok("同步标签引用计数", code == 200 and tag_sync.get("ok"), tag_sync)

    section("14. 发布账号独立模块")
    code, acc = req("POST", "/publish-accounts", {
        "name": PREFIX + "发布账号", "platform": "抖音", "account_id": PREFIX + "uid",
        "video_count": 12, "likes_count": 35000, "followers_count": 8600,
        "tags": [PREFIX + "账号标签"], "note": "冒烟账号"})
    ok("新建发布账号", code == 200 and acc.get("id"), acc.get("name") if isinstance(acc, dict) else acc)
    acc_id = acc.get("id") if isinstance(acc, dict) else None
    if acc_id:
        CREATED.setdefault("accounts", []).append(acc_id)
        ok("账号含视频数量/获赞/粉丝", acc.get("video_count") == 12 and acc.get("likes_count") == 35000
           and acc.get("followers_count") == 8600, acc)
        code, accs = req("GET", "/publish-accounts")
        ok("发布账号列表可读", code == 200 and any(a["id"] == acc_id for a in accs),
           "count=%s" % len(accs) if isinstance(accs, list) else accs)
        code, acc_up = req("PUT", "/publish-accounts/%s" % acc_id, {"followers_count": 9999})
        ok("部分更新保留账号名", code == 200 and acc_up.get("followers_count") == 9999
           and acc_up.get("name") == PREFIX + "发布账号", acc_up.get("name") if isinstance(acc_up, dict) else acc_up)
        code, acc_videos = req("GET", "/publish-accounts/%s/videos" % acc_id)
        ok("账号视频列表接口", code == 200 and "items" in acc_videos, acc_videos)

    section("15. 流程字段：封面 / 类别 / 标签 / 成片 / 发布账号")
    code, cat_list = req("GET", "/categories")
    cat_id2 = cat_list[0]["id"] if cat_list else None
    code, idea_f = req("POST", "/ideas", {
        "title": PREFIX + "封面创意", "cover": "/uploads/2026-01/cover.png",
        "category_id": cat_id2, "tags": [PREFIX + "流程标签"], "douyin_url": "https://v.douyin.com/smoke_field_001/"})
    ok("创意含封面与类别", code == 200 and idea_f.get("cover") == "/uploads/2026-01/cover.png"
       and idea_f.get("category_id") == cat_id2, idea_f.get("cover") if isinstance(idea_f, dict) else idea_f)
    ok("创意回填类别名称", idea_f.get("category_name") is not None, idea_f.get("category_name"))
    idea_f_id = idea_f.get("id") if isinstance(idea_f, dict) else None
    if idea_f_id:
        CREATED["ideas"].append(idea_f_id)
        code, prod_f = req("POST", "/productions", {
            "title": idea_f.get("title"), "cover": idea_f.get("cover"),
            "tags": [PREFIX + "流程标签"], "category_id": cat_id2,
            "platform": "硬核", "prompt": [{"seg": "", "text": "字段制作"}],
            "status": "制作中", "idea_id": idea_f_id})
        ok("由创意直接创建制作记录", code == 200 and prod_f.get("id"), prod_f)
        prod_f_id = prod_f.get("id") if isinstance(prod_f, dict) else None
        if prod_f_id:
            CREATED["productions"].append(prod_f_id)
            code, prod_chk = req("GET", "/productions/%s" % prod_f_id)
            ok("制作继承封面与标签", prod_chk.get("cover") == "/uploads/2026-01/cover.png"
               and prod_chk.get("tags") == [PREFIX + "流程标签"], prod_chk.get("tags"))
            if acc_id:
                    code, pub_f = req("PUT", "/productions/%s" % prod_f_id, {
                        "status": "已完成", "publish_platform": "抖音",
                        "publish_account_id": acc_id, "video_file": "/uploads/2026-01/out.mp4",
                        "tags": [PREFIX + "流程标签"], "published_at": "2026-01-01T10:00:00"})
                    ok("成片与发布账号关联", code == 200 and pub_f.get("video_file") == "/uploads/2026-01/out.mp4"
                       and pub_f.get("publish_account_name") == PREFIX + "发布账号",
                       pub_f.get("publish_account_name") if isinstance(pub_f, dict) else pub_f)
                    code, sum_f = req("GET", "/publish-stats/summary")
                    row_f = next((x for x in sum_f.get("items", []) if x["production_id"] == prod_f_id), None)
                    ok("汇总含成片与发布账号", row_f is not None and row_f.get("video_file") == "/uploads/2026-01/out.mp4"
                       and row_f.get("publish_account_name") == PREFIX + "发布账号",
                       row_f.get("publish_account_name") if row_f else None)
                    ok("汇总含视频标签", row_f is not None and row_f.get("tags") == [PREFIX + "流程标签"],
                       row_f.get("tags") if row_f else None)
                    code, _ = req("DELETE", "/publish-accounts/%s" % acc_id)
                    ok("有视频关联的账号不可删除", code == 400, "code=%s" % code)

    section("15b. 视频分类：颜色 / 图片图标 / 展示方式")
    code, cats_color = req("GET", "/categories")
    ok("分类返回颜色与展示字段", code == 200 and isinstance(cats_color, list)
       and all(all(k in c for k in ("color", "image", "display")) for c in cats_color),
       cats_color[0] if cats_color else None)
    if cat_id:
        code, cat_col = req("PUT", "/categories/%s" % cat_id,
                            {"name": PREFIX + "分类改", "color": "#123456",
                             "image": "/uploads/test-category.png", "display": "icon", "sort": 98})
        ok("修改分类颜色 / 图标 / 展示方式", code == 200
           and cat_col.get("color") == "#123456"
           and cat_col.get("image") == "/uploads/test-category.png"
           and cat_col.get("display") == "icon",
           cat_col if isinstance(cat_col, dict) else cat_col)

    section("15c. 数据中心：按账号细分")
    code, acc = req("POST", "/publish-accounts", {
        "name": PREFIX + "细分账号", "platform": "抖音", "account_id": "seg_douyin"})
    ok("新建细分用发布账号", code == 200 and acc.get("id"), acc.get("name") if isinstance(acc, dict) else acc)
    seg_acc_id = acc.get("id") if isinstance(acc, dict) else None
    if seg_acc_id:
        CREATED["accounts"].append(seg_acc_id)
    code, summ_all = req("GET", "/publish-stats/summary")
    ok("汇总返回账号分组列表", code == 200 and isinstance(summ_all.get("accounts"), list),
       "groups=%s" % len(summ_all.get("accounts", [])))
    ok("账号分组含数量与指标", isinstance(summ_all.get("accounts"), list)
       and all(all(k in g for k in ("key", "name", "count", "plays")) for g in summ_all["accounts"]),
       summ_all.get("accounts", [])[:1])
    # 用某个分组的 key 过滤：返回的每条都应属于该账号（分组 count 是账号资料作品数，
    # 与系统内已录入数据的成片条数不是一回事，不能按数量比对）
    if summ_all.get("accounts"):
        target = summ_all["accounts"][0]
        code, summ_one = req("GET", "/publish-stats/summary?account_key=" + str(target["key"]))
        rows = summ_one.get("items", []) if code == 200 else []
        belongs = all(x.get("account_key") == target["key"] for x in rows)
        ok("按账号 key 过滤汇总", code == 200 and belongs
           and summ_one.get("account_key") == target["key"],
           "got=%s items=%s" % (code, len(rows)))

    section("15d. 素材共享：自定义素材库与素材 CRUD")
    code, lib = req("POST", "/material-libraries", {"name": PREFIX + "素材库", "color": "#4a7cc4"})
    ok("新建自定义素材库", code == 200 and lib.get("id"), lib.get("name") if isinstance(lib, dict) else lib)
    lib_id = lib.get("id") if isinstance(lib, dict) else None
    if lib_id:
        CREATED["material_libraries"].append(lib_id)
        code, libs = req("GET", "/material-libraries")
        ok("素材库列表包含新项", any(x["id"] == lib_id for x in libs))
        code, lib2 = req("PUT", "/material-libraries/%s" % lib_id,
                         {"name": PREFIX + "素材库改", "color": "#7b62c9"})
        ok("修改素材库名称与颜色", code == 200 and lib2.get("name") == PREFIX + "素材库改"
           and lib2.get("color") == "#7b62c9", lib2.get("name") if isinstance(lib2, dict) else lib2)
        code, mat = req("POST", "/material-libraries/%s/materials" % lib_id, {
            "name": PREFIX + "素材", "description": "共享素材测试", "tags": ["共享"],
            "images": [{"file_path": "/uploads/test.png", "sort": 0}]})
        ok("新建共享素材", code == 200 and mat.get("id") and mat.get("library_id") == lib_id,
           mat.get("name") if isinstance(mat, dict) else mat)
        mat_id = mat.get("id") if isinstance(mat, dict) else None
        if mat_id:
            CREATED["materials"].append(mat_id)
            code, mats = req("GET", "/material-libraries/%s/materials" % lib_id)
            ok("素材列表包含新项", any(x["id"] == mat_id for x in mats))
            code, mat2 = req("PUT", "/material-libraries/materials/%s" % mat_id, {
                "name": PREFIX + "素材改", "description": "改后", "tags": ["共享", "改"],
                "images": [{"file_path": "/uploads/test.png", "sort": 0}]})
            ok("修改共享素材", code == 200 and mat2.get("name") == PREFIX + "素材改"
               and len(mat2.get("images", [])) == 1, mat2.get("name") if isinstance(mat2, dict) else mat2)
            # 库内有素材时禁止删除素材库
            code, _ = req("DELETE", "/material-libraries/%s" % lib_id)
            ok("非空素材库禁止删除", code == 400, "code=%s" % code)
        code, default_libs = req("GET", "/material-libraries")
        ok("默认素材库已初始化", any(x.get("name") == "人物库" for x in default_libs)
           and any(x.get("name") == "服装库" for x in default_libs),
           [x.get("name") for x in default_libs])

    section("15e. 投票规则：每人每天上限可配置且生效")
    code, vote_cfg = req("GET", "/settings/vote")
    ok("投票规则配置可读", code == 200 and isinstance((vote_cfg.get("vote") or {}).get("daily_limit"), int),
       vote_cfg.get("vote"))
    old_limit = (vote_cfg.get("vote") or {}).get("daily_limit", 5)
    # 暂时把上限调为 1，另一个测试账号投两条不同的创意应被拦截
    req("PUT", "/settings", {"key": "vote", "value": {"daily_limit": 1}})
    # 先清理可能残留的同名测试用户（命中用户名占用时重新登录）
    code, existing_users = req("GET", "/users")
    if code == 200 and isinstance(existing_users, list):
        for u in existing_users:
            if u.get("username") == PREFIX + "voter":
                req("DELETE", "/users/%s" % u["id"])
    code, reg = req("POST", "/auth/register", {
        "username": PREFIX + "voter", "password": "test123456", "nickname": PREFIX + "投票者"})
    voter_token = None
    if code in (200, 201) and isinstance(reg, dict) and (reg.get("user") or {}).get("id"):
        CREATED["users"].append(reg["user"]["id"])
        voter_token = reg.get("token")
    code, idea_a = req("POST", "/ideas", {"title": PREFIX + "投票A"})
    idea_a_id = idea_a.get("id") if isinstance(idea_a, dict) else None
    if idea_a_id:
        CREATED["ideas"].append(idea_a_id)
    code, idea_b = req("POST", "/ideas", {"title": PREFIX + "投票B"})
    idea_b_id = idea_b.get("id") if isinstance(idea_b, dict) else None
    if idea_b_id:
        CREATED["ideas"].append(idea_b_id)
    if voter_token and idea_a_id and idea_b_id:
        code, va = req("POST", "/ideas/%s/vote" % idea_a_id, {}, token=voter_token)
        ok("规则生效：首票成功", code == 200 and va.get("votes") == 1,
           "votes=%s" % va.get("votes"))
        code, vb = req("POST", "/ideas/%s/vote" % idea_b_id, {}, token=voter_token)
        ok("规则生效：超出每日上限被拦截", code == 400 and "上限" in str(vb),
           "code=%s detail=%s" % (code, vb))
        code, vdetail = req("GET", "/ideas/%s" % idea_a_id, token=voter_token)
        ok("详情返回投票额度字段", vdetail.get("vote_daily_limit") == 1
           and vdetail.get("vote_used_today") == 1 and vdetail.get("vote_exhausted") is True,
           "limit=%s used=%s" % (vdetail.get("vote_daily_limit"), vdetail.get("vote_used_today")))
        code, vc = req("POST", "/ideas/%s/vote" % idea_a_id, {}, token=voter_token)
        ok("取消投票返还额度", code == 200 and vc.get("vote_used_today") == 0,
           "used=%s" % vc.get("vote_used_today"))
    req("PUT", "/settings", {"key": "vote", "value": {"daily_limit": old_limit}})
    ok("投票规则已还原", True)

    section("15f. 数据中心状态：正常/隐藏")
    code, summ0 = req("GET", "/publish-stats/summary")
    ok("汇总含记录状态统计", code == 200 and "status_counts" in summ0, summ0.get("status_counts") if isinstance(summ0, dict) else summ0)
    ok("汇总项含 data_status 字段", bool(summ0.get("items")) and "data_status" in summ0["items"][0],
       summ0["items"][0].get("data_status") if summ0.get("items") else None)
    ok("汇总返回未录入条数", isinstance(summ0.get("unrecorded_count"), int)
       and summ0["unrecorded_count"] >= 0, summ0.get("unrecorded_count"))
    ok("汇总含正常口径条数与展示行数", code == 200
       and isinstance(summ0.get("count"), int) and isinstance(summ0.get("row_count"), int)
       and summ0["count"] <= summ0["row_count"],
       "count=%s row_count=%s" % (summ0.get("count"), summ0.get("row_count")))
    # 找一条已发布制作记录切换隐藏再恢复
    target_pid = summ0["items"][0]["production_id"] if summ0.get("items") else None
    if target_pid:
        total_before = summ0["total"]["plays"]
        hidden_item = next((i for i in summ0["items"] if i["data_status"] == "正常"), None)
        if hidden_item:
            pid = hidden_item["production_id"]
            code, hid = req("PUT", "/publish-stats/status/%s" % pid, {"status": "隐藏"})
            ok("记录状态可切换为隐藏", code == 200 and hid.get("data_status") == "隐藏", hid)
            code, summ_h = req("GET", "/publish-stats/summary")
            ok("隐藏记录默认仍显示但不计入KPI",
               any(i["production_id"] == pid and i["data_status"] == "隐藏" for i in summ_h["items"])
               and summ_h["total"]["plays"] + hidden_item["plays"] == total_before,
               "before=%s after=%s" % (total_before, summ_h["total"]["plays"]))
            ok("隐藏后正常口径条数减一", summ_h.get("count") == summ0.get("count", 0) - 1,
               "before=%s after=%s" % (summ0.get("count"), summ_h.get("count")))
            hidden_actual = sum(1 for i in summ_h["items"] if i["data_status"] == "隐藏")
            ok("隐藏标签数量等于实际隐藏行数", summ_h.get("status_counts", {}).get("隐藏") == hidden_actual,
               "label=%s actual=%s" % (summ_h.get("status_counts", {}).get("隐藏"), hidden_actual))
            code, filt_h = req("GET", "/publish-stats/summary?data_status=" + "隐藏")
            ok("可按隐藏状态筛选", code == 200 and all(i["data_status"] == "隐藏" for i in filt_h["items"]),
               "count=%s" % len(filt_h["items"]))
            ok("切换隐藏筛选不重置KPI与统计条数",
               filt_h.get("total", {}).get("plays") == summ_h["total"]["plays"]
               and filt_h.get("count") == summ_h.get("count"),
               "total=%s/%s count=%s/%s" % (filt_h.get("total", {}).get("plays"), summ_h["total"]["plays"],
                                            filt_h.get("count"), summ_h.get("count")))
            req("PUT", "/publish-stats/status/%s" % pid, {"status": "正常"})
            ok("记录状态已恢复正常", True)
        # 非法状态校验
        code, bad = req("PUT", "/publish-stats/status/%s" % target_pid, {"status": "无效状态"})
        ok("非法记录状态返回 400", code == 400, bad)
        code, deleted = req("PUT", "/publish-stats/status/%s" % target_pid, {"status": "删除"})
        ok("已下线的删除状态返回 400", code == 400, deleted)

    section("15g. 我的账号扩展字段：状态/更新节奏/责任人")
    code, creators = req("GET", "/publish-accounts/creators")
    ok("责任人候选仅创作角色", code == 200 and isinstance(creators, list) and len(creators) >= 1
       and all(c.get("role") == "creator" for c in creators),
       "count=%s" % len(creators) if isinstance(creators, list) else creators)
    creator_id = creators[0]["id"] if isinstance(creators, list) and creators else None
    code, acc_ext = req("POST", "/publish-accounts", {
        "name": PREFIX + "扩展账号", "platform": "抖音",
        "status": "搁置", "update_rhythm": "周更", "responsible_id": creator_id})
    ok("账号含状态/节奏/责任人字段", code == 200 and acc_ext.get("status") == "搁置"
       and acc_ext.get("update_rhythm") == "周更" and acc_ext.get("responsible_id") == creator_id
       and bool(acc_ext.get("responsible_name")), acc_ext)
    acc_ext_id = acc_ext.get("id") if isinstance(acc_ext, dict) else None
    if acc_ext_id:
        CREATED.setdefault("accounts", []).append(acc_ext_id)
        code, bad = req("POST", "/publish-accounts", {"name": PREFIX + "非法账号", "status": "非法"})
        ok("非法账号状态返回 400", code == 400, bad)
        code, bad2 = req("POST", "/publish-accounts", {"name": PREFIX + "非法节奏账号", "update_rhythm": "月更"})
        ok("非法更新节奏返回 400", code == 400, bad2)

    section("15h. 更新提醒：按节奏计算 + 联动创意")
    # 自建一个非抖音（视为在线）且从未发布的账号，避免依赖预置演示数据
    code, acc_online = req("POST", "/publish-accounts", {
        "name": PREFIX + "在线账号", "platform": "小红书", "update_rhythm": "日更"})
    if isinstance(acc_online, dict) and acc_online.get("id"):
        CREATED.setdefault("accounts", []).append(acc_online["id"])
    ok("在线账号创建用于提醒校验", code == 200 and bool(acc_online.get("id")), acc_online)
    code, reminders = req("GET", "/publish-accounts/reminders")
    ok("更新提醒接口可用", code == 200 and isinstance(reminders, list), reminders)
    ok("提醒项含到期计算字段", not reminders or all(
        "account_id" in r and "update_rhythm" in r and "is_due" in r and "reason" in r
        and "kind" in r and "is_offline" in r and "action_label" in r for r in reminders))
    offline_reminders = [r for r in reminders if r.get("kind") == "offline"]
    ok("离线账号推送到更新提醒", len(offline_reminders) > 0
       and all("自动更新已跳过" in r.get("reason", "") for r in offline_reminders),
       "count=%s" % len(offline_reminders))
    ok("离线提醒操作为去登录", all(r.get("action_label") == "去登录" for r in offline_reminders))
    # 从未发布且「正常在线」状态的账号视为到期（离线账号单独提示重新扫码）
    never = next((r for r in reminders if r["days_since"] == -1 and r["is_due"] is True
                  and not r.get("is_offline")), None)
    ok("从未发布账号视为到期", bool(never) and never["reason"].startswith("从未发布"), never)
    code, only_due = req("GET", "/publish-accounts/reminders?only_due=1")
    ok("仅到期过滤生效", code == 200 and all(r["is_due"] for r in only_due),
       "count=%s" % len(only_due))
    # 搁置账号不出现在提醒列表
    if acc_ext_id:
        ok("搁置账号不参与提醒", not any(r["account_id"] == acc_ext_id for r in reminders))
        # 一键排期：生成联动账号的「未使用 + 备选标记」创意（搁置账号也可手动排期）
        code, sched_idea = req("POST", "/publish-accounts/%s/schedule" % acc_ext_id, {})
        ok("更新提醒一键排期生成创意", code == 200 and sched_idea.get("id")
           and sched_idea.get("account_id") == acc_ext_id and sched_idea.get("status") == "未使用",
           sched_idea)
        if sched_idea.get("id"):
            CREATED.setdefault("ideas", []).append(sched_idea["id"])
            code, si = req("GET", "/ideas/%s" % sched_idea["id"])
            ok("一键排期创意状态与创作人正确", code == 200 and si.get("status") == "未使用"
               and si.get("is_backup") is True
               and si.get("creator_id") == creator_id, si.get("status") if isinstance(si, dict) else si)
            ok("一键排期创意备注含账号", PREFIX + "扩展账号" in (si.get("remark") or ""),
               si.get("remark") if isinstance(si, dict) else si)

    section("15i. 自动更新：离线跳过 + 账号历史快照")
    code, au_status = req("GET", "/auto-update/status")
    ok("自动更新状态接口可用", code == 200 and isinstance(au_status.get("config"), dict)
       and "active_accounts" in au_status, au_status if isinstance(au_status, dict) else au_status)
    if acc_id:
        code, au_run = req("POST", "/auto-update/run", {"account_ids": [acc_id], "force": True})
        ok("离线账号自动更新不执行采集", code == 200 and au_run.get("offline") == 1
           and au_run.get("updated") == 0 and au_run.get("videos_created") == 0,
           au_run.get("message") if isinstance(au_run, dict) else au_run)
        ok("离线跳过明细可追踪", isinstance(au_run.get("details"), list)
           and au_run["details"][0].get("status") == "offline", au_run.get("details"))
        code, snaps0 = req("GET", "/auto-update/snapshots?account_id=%s" % acc_id)
        ok("离线账号不生成快照", code == 200 and isinstance(snaps0, list) and len(snaps0) == 0, snaps0)
        # 写入一条测试快照验证查询接口；随账号清理一并删除
        c = sqlite3.connect(DB_PATH)
        try:
            c.execute(
                "INSERT INTO publish_account_snapshots "
                "(account_id, account_name, video_count, likes_count, followers_count, "
                " prev_video_count, prev_likes_count, prev_followers_count, "
                " fetched_video_count, source, note, snapshot_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                (acc_id, PREFIX + "发布账号", 13, 36000, 8700, 11, 34000, 8500, 20, "auto", "冒烟快照",
                 datetime.now().isoformat(sep=" ")),
            )
            c.commit()
        finally:
            c.close()
        code, snaps = req("GET", "/auto-update/snapshots?account_id=%s" % acc_id)
        ok("账号历史快照可读", code == 200 and isinstance(snaps, list) and len(snaps) == 1
           and snaps[0].get("video_count") == 13 and snaps[0].get("followers_count") == 8700
           and snaps[0].get("source") == "auto", snaps)
        ok("快照含作品数量与账号指标", all(k in snaps[0] for k in
           ["video_count", "likes_count", "followers_count", "fetched_video_count", "snapshot_at"]), snaps[0])
        ok("快照自包含更新前基准值", snaps[0].get("prev_video_count") == 11
           and snaps[0].get("prev_likes_count") == 34000
           and snaps[0].get("prev_followers_count") == 8500, snaps[0])
        # 账号列表 deltas：最新快照自带 prev_* 时直接用它算增量，首次更新也能显示
        # 先把账号值固定为已知值，避免前面步骤改动干扰断言
        req("PUT", "/publish-accounts/%s" % acc_id,
            {"video_count": 12, "likes_count": 35000, "followers_count": 8600})
        code, acc_list = req("GET", "/publish-accounts")
        hit = next((a for a in acc_list if a.get("id") == acc_id), {}) if code == 200 else {}
        ok("账号列表返回自包含增量", hit.get("deltas") == {
            "video_count": 1, "likes_count": 1000, "followers_count": 100
        }, hit.get("deltas"))

    section("16. 抖音采集通道：失败可降级且提示明确")
    code, fetch_acc = req("POST", "/douyin/account/fetch", {"query": "smoke_test_uid", "channel": "official"})
    ok("账号采集失败返回可读提示", code == 200 and fetch_acc.get("ok") is False
       and bool(fetch_acc.get("message")), fetch_acc.get("message") if isinstance(fetch_acc, dict) else fetch_acc)
    ok("采集失败给出手工录入指引", bool((fetch_acc.get("data") or {}).get("manual_required")),
       fetch_acc.get("data") if isinstance(fetch_acc, dict) else None)
    code, fetch_st = req("POST", "/douyin/stats/fetch", {"url": "https://v.douyin.com/smoke_fetch_001/", "channel": "official"})
    ok("视频采集失败返回可读提示", code == 200 and fetch_st.get("ok") is False
       and bool(fetch_st.get("message")), fetch_st.get("message") if isinstance(fetch_st, dict) else fetch_st)

    section("16b. 扫码登录失败保护：依赖缺失不静默建号")
    try:
        import tempfile
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models import User, PublishAccount
        from app.schemas import DouyinLoginIn
        from app.routers import douyin_collect as dc2
        import app.douyin_collector as dcol

        # 依赖目录不存在时，采集器必须明确抛错，不能返回空字典被当成登录成功
        _old_modules = dcol._NODE_MODULES
        dcol._NODE_MODULES = os.path.join(tempfile.gettempdir(), "__AVM_NO_NODE_MODULES__")
        try:
            try:
                dcol.login_douyin(PREFIX + "profile")
                ok("扫码登录依赖缺失时明确报错", False, "未抛异常")
            except dcol.CollectError as exc:
                ok("扫码登录依赖缺失时明确报错",
                   "依赖缺失" in exc.message and bool(exc.manual_hint), exc.message)
        finally:
            dcol._NODE_MODULES = _old_modules

        # 登录态为空时，路由不得建号、不得标记已登录
        _engine2 = create_engine("sqlite:///" + DB_PATH.replace("\\", "/"),
                                 connect_args={"check_same_thread": False})
        s2 = sessionmaker(bind=_engine2)()
        try:
            admin = s2.query(User).filter(User.username == "admin").first()
            before = s2.query(PublishAccount).count()
            _old_login = dc2.login_douyin
            dc2.login_douyin = lambda *a, **k: {}
            try:
                res = dc2.douyin_login(DouyinLoginIn(), s2, admin)
            finally:
                dc2.login_douyin = _old_login
            after = s2.query(PublishAccount).count()
            ok("登录态为空时不建号且不误标已登录",
               res.get("ok") is False and after == before, res)
        finally:
            s2.close()
    except Exception as exc:
        ok("扫码登录失败保护", False, str(exc))

    section("17. 创意灵感：评论 / 我想做 / 视频数据")
    code, c_idea = req("POST", "/ideas", {
        "title": PREFIX + "评论创意",
        "author": "测试作者",
        "like_count": 1200, "comment_count": 34, "collect_count": 56, "share_count": 7,
    })
    ok("创建带视频数据的创意", code == 200 and c_idea.get("like_count") == 1200
       and c_idea.get("comment_count") == 34 and c_idea.get("collect_count") == 56
       and c_idea.get("share_count") == 7, c_idea if isinstance(c_idea, dict) else c_idea)
    c_idea_id = c_idea.get("id") if isinstance(c_idea, dict) else None
    if c_idea_id:
        CREATED["ideas"].append(c_idea_id)
        code, c_list = req("GET", "/ideas/%s" % c_idea_id)
        ok("创意详情回显视频数据", code == 200 and c_list.get("like_count") == 1200
           and c_list.get("share_count") == 7, c_list.get("like_count") if isinstance(c_list, dict) else c_list)

        # 我想做：认领标记，可切换，不改变流程状态
        code, w1 = req("POST", "/ideas/%s/want" % c_idea_id)
        ok("标记「我想做」成功", code == 200 and w1.get("wanted") is True and w1.get("wants") == 1,
           w1.get("wants") if isinstance(w1, dict) else w1)
        ok("「我想做」不改变创意状态", w1.get("status") == "未使用", w1.get("status"))
        code, w2 = req("POST", "/ideas/%s/want" % c_idea_id)
        ok("再次点击取消「我想做」", code == 200 and w2.get("wanted") is False and w2.get("wants") == 0,
           w2.get("wants") if isinstance(w2, dict) else w2)

        # 评论：多人可发表意见
        code, cmt1 = req("POST", "/ideas/%s/comments" % c_idea_id, {"content": "这个创意很好"})
        ok("发表评论成功", code == 200 and cmt1.get("content") == "这个创意很好"
           and bool(cmt1.get("user_name")), cmt1.get("content") if isinstance(cmt1, dict) else cmt1)
        code, cmt_list = req("GET", "/ideas/%s/comments" % c_idea_id)
        ok("评论列表可读取", code == 200 and len(cmt_list) == 1, len(cmt_list) if isinstance(cmt_list, list) else cmt_list)
        code, empty_cmt = req("POST", "/ideas/%s/comments" % c_idea_id, {"content": "   "})
        ok("空评论被拒绝", code == 400, "code=%s" % code)
        code, c_detail = req("GET", "/ideas/%s" % c_idea_id)
        ok("创意详情带评论条数", code == 200 and c_detail.get("comment_total") == 1,
           c_detail.get("comment_total") if isinstance(c_detail, dict) else c_detail)
        if isinstance(cmt1, dict) and cmt1.get("id"):
            code, cmt_del = req("DELETE", "/ideas/%s/comments/%s" % (c_idea_id, cmt1["id"]))
            ok("删除自己的评论", code == 200, "code=%s" % code)
            code, cmt_list2 = req("GET", "/ideas/%s/comments" % c_idea_id)
            ok("删除后评论列表为空", code == 200 and len(cmt_list2) == 0,
               len(cmt_list2) if isinstance(cmt_list2, list) else cmt_list2)

    section("18. 模块角色权限：菜单与按钮")
    code, roles = req("GET", "/roles")
    ok("读取角色列表", code == 200 and isinstance(roles, list) and len(roles) >= 4,
       len(roles) if isinstance(roles, list) else roles)
    role_keys = [r.get("key") for r in roles] if isinstance(roles, list) else []
    ok("内置四种模块角色", set(["super", "inspiration", "production", "operation"]).issubset(set(role_keys)), role_keys)
    super_role = next((r for r in roles if r.get("key") == "super"), {}) if isinstance(roles, list) else {}
    insp_role = next((r for r in roles if r.get("key") == "inspiration"), {}) if isinstance(roles, list) else {}
    expect_menus = {"dashboard", "ideas", "productions", "publish-stats", "publish-accounts",
                    "characters", "materials", "users", "roles", "settings"}
    ok("超管拥有全部菜单且不含已下线模块", set(super_role.get("menus", [])) == expect_menus,
       super_role.get("menus"))
    ok("超管拥有全部按钮", len(super_role.get("buttons", [])) >= 25, len(super_role.get("buttons", [])))
    ok("灵感角色菜单少于超管", len(insp_role.get("menus", [])) < len(super_role.get("menus", [])),
       len(insp_role.get("menus", [])))
    ok("灵感角色不含配置中心菜单", "settings" not in insp_role.get("menus", []), insp_role.get("menus"))
    ok("灵感角色不含数据中心菜单", "publish-stats" not in insp_role.get("menus", []), insp_role.get("menus"))
    ok("灵感角色不含角色权限菜单", "roles" not in insp_role.get("menus", []), insp_role.get("menus"))

    code, catalog = req("GET", "/roles/catalog")
    ok("读取权限可选项目录", code == 200 and catalog.get("menus") and catalog.get("buttons"),
       list(catalog.keys()))
    code, myperm = req("GET", "/roles/mine")
    ok("读取当前用户权限", code == 200 and myperm.get("role") == "super"
       and "ideas" in myperm.get("menus", []), myperm.get("role"))
    code, auth_perm = req("GET", "/auth/permissions")
    ok("鉴权接口同步返回权限", code == 200 and auth_perm.get("role") == "super", auth_perm.get("role"))

    # 新建一个「灵感」角色的账号，验证菜单与按钮限制
    role_uname = PREFIX.lower() + "insp"
    code, ru = req("POST", "/users", {"username": role_uname, "password": "test123456",
                                      "nickname": "测试灵感", "role": "creator",
                                      "module_role": "inspiration",
                                      "can_create": True, "can_view_all": True})
    ok("新建指定模块角色的用户", code == 200 and ru.get("module_role") == "inspiration",
       ru.get("module_role") if isinstance(ru, dict) else ru)
    ru_id = ru.get("id") if isinstance(ru, dict) else None
    if ru_id:
        CREATED["users"].append(ru_id)
        code, rlogin = req("POST", "/auth/login", {"username": role_uname, "password": "test123456"})
        rtoken = rlogin.get("token") if isinstance(rlogin, dict) else None
        ok("模块角色用户可登录", code == 200 and bool(rtoken), "code=%s" % code)
        code, rperm = req("GET", "/roles/mine", token=rtoken)
        ok("灵感角色生效：菜单受限", code == 200 and rperm.get("role") == "inspiration"
           and "settings" not in rperm.get("menus", []) and "ideas" in rperm.get("menus", []),
           rperm.get("menus") if isinstance(rperm, dict) else rperm)
        ok("灵感角色生效：按钮受限", "ideas.create" in rperm.get("buttons", [])
           and "settings.manage" not in rperm.get("buttons", []),
           rperm.get("buttons") if isinstance(rperm, dict) else rperm)
        code, rstats = req("POST", "/publish-stats", {"production_id": 1}, token=rtoken)
        ok("灵感角色无法录入发布数据（按钮权限拦截）", code == 403, "code=%s" % code)
        code, rupd = req("PUT", "/roles/%s" % "inspiration", {"menus": ["ideas"]}, token=rtoken)
        ok("非超管修改角色权限被拒绝", code == 403, "code=%s" % code)
        code, rrole_upd = req("PUT", "/roles/users/%s" % ru_id, {"module_role": "operation"})
        ok("超管调整用户模块角色", code == 200 and rrole_upd.get("module_role") == "operation",
           rrole_upd.get("module_role") if isinstance(rrole_upd, dict) else rrole_upd)
        code, rperm2 = req("GET", "/roles/mine", token=rtoken)
        ok("调整后模块角色立即生效", code == 200 and rperm2.get("role") == "operation",
           rperm2.get("role") if isinstance(rperm2, dict) else rperm2)

    section("19. 配置中心：平台图片图标与模块统一展示方式")
    code, plat_set = req("GET", "/settings/platforms")
    ok("制作平台配置带图片与展示字段", code == 200 and plat_set.get("platforms")
       and all(all(k in p for k in ("color", "image", "display"))
               for p in plat_set.get("platforms", [])),
       plat_set.get("platforms"))
    code, pub_set = req("GET", "/settings/publish_platforms")
    ok("发布平台配置带图片与展示字段", code == 200 and pub_set.get("publish_platforms")
       and all(all(k in p for k in ("color", "image", "display"))
               for p in pub_set.get("publish_platforms", [])),
       pub_set.get("publish_platforms"))
    # 三个模块级显示方式配置（集中存于 platform_display）
    code, disp_check0 = req("GET", "/settings/platform_display")
    pd0 = disp_check0.get("platform_display", {})
    ok("三个模块默认展示方式均为全显", code == 200
       and all(pd0.get(k) == "full" for k in ("category", "platform", "publish")), pd0)
    code, disp_upd = req("PUT", "/settings", {"key": "platform_display", "value": {
        "mode": "full", "category": "label", "platform": "icon", "publish": "label"}})
    ok("三个模块展示方式可分别切换", code == 200, "code=%s" % code)
    code, disp_check = req("GET", "/settings/platform_display")
    pd = disp_check.get("platform_display", {})
    ok("三个模块展示方式切换已持久化", code == 200
       and pd.get("category") == "label" and pd.get("platform") == "icon" and pd.get("publish") == "label", pd)
    req("PUT", "/settings", {"key": "platform_display", "value": {
        "mode": "full", "category": "full", "platform": "full", "publish": "full"}})
    code, plat_upd = req("PUT", "/settings", {"key": "platforms", "value": [
        {"name": "测试平台", "color": "#4a7cc4", "image": "/uploads/test-platform.png", "display": "icon"}]})
    ok("制作平台图片可保存", code == 200, "code=%s" % code)
    code, plat_check = req("GET", "/settings/platforms")
    first_plat = (plat_check.get("platforms") or [{}])[0]
    ok("制作平台图片已持久化", code == 200
       and first_plat.get("image") == "/uploads/test-platform.png"
       and first_plat.get("display") == "icon", first_plat)
    code, pub_upd = req("PUT", "/settings", {"key": "publish_platforms", "value": [
        {"name": "测试发布平台", "color": "#e05c4b", "image": "/uploads/test-publish.png", "display": "label"}]})
    ok("发布平台图片可保存", code == 200, "code=%s" % code)
    code, pub_check = req("GET", "/settings/publish_platforms")
    first_pub = (pub_check.get("publish_platforms") or [{}])[0]
    ok("发布平台图片已持久化", code == 200
       and first_pub.get("image") == "/uploads/test-publish.png"
       and first_pub.get("display") == "label", first_pub)
    # 还原平台配置
    req("PUT", "/settings", {"key": "platforms", "value": plat_set.get("platforms")})
    req("PUT", "/settings", {"key": "publish_platforms", "value": pub_set.get("publish_platforms")})

    section("19b. 配置删除规则：关联禁止 / 无关联可删 / 即时生效")
    temp_name = PREFIX + "临时平台"
    req("PUT", "/settings", {"key": "platforms", "value": list(plat_set.get("platforms") or []) + [
        {"name": temp_name, "color": "#123456", "image": "", "display": "full"}]})
    code, _ = req("DELETE", "/settings/option?key=platforms&name=" + temp_name)
    ok("无关联配置选项可删除", code == 200, "code=%s" % code)
    code, after_del = req("GET", "/settings/platforms")
    ok("删除后配置即时生效", code == 200 and all(
        p.get("name") != temp_name for p in after_del.get("platforms", [])), "code=%s" % code)
    code, prods = req("GET", "/productions?page=1&page_size=100")
    used_platform = next((p.get("platform") for p in (prods or {}).get("items", []) if p.get("platform")), "")
    if used_platform:
        code, denied = req("DELETE", "/settings/option?key=platforms&name=" + used_platform)
        ok("被业务记录引用的平台禁止删除", code == 400, "code=%s detail=%s" % (code, denied))
    req("PUT", "/settings", {"key": "platforms", "value": plat_set.get("platforms")})

    # 手动「更新」作为总入口：进程内注入 mock 采集，验证同时写账号快照 + 发布数据
    section("15j. 账号更新总入口：账号数据 + 发布数据同步")
    try:
        import sys, os
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        from app.models import User, PublishAccount, DouyinImport, PublishAccountSnapshot
        from app.schemas import DouyinAccountSyncOneIn
        from app.routers import douyin_collect as dc
        import app.auto_update_service as aus

        # 显式指向冒烟库，避免 SessionLocal 受 cwd 影响连错文件
        _engine = create_engine("sqlite:///" + DB_PATH.replace("\\", "/"),
                                connect_args={"check_same_thread": False})
        s = sessionmaker(bind=_engine)()
        test_user = s.query(User).filter(User.username == "admin").first()
        test_acc = s.query(PublishAccount).filter(PublishAccount.name == PREFIX + "发布账号").first()
        if test_user and test_acc:
            vid = PREFIX + "manual_sync_vid"
            s.query(DouyinImport).filter(DouyinImport.video_id == vid).delete()
            before_pub = s.query(DouyinImport).filter(DouyinImport.account_id == test_acc.id).count()
            before_snap = s.query(PublishAccountSnapshot).filter(PublishAccountSnapshot.account_id == test_acc.id).count()

            def _fake_acc(query, channel, profile_key=None):
                return {"name": test_acc.name, "video_count": 99, "likes_count": 9999,
                        "followers_count": 8888, "douyin_uid": test_acc.douyin_uid}

            def _fake_videos(query, limit, profile_key=None):
                return {"videos": [{"video_id": vid, "title": PREFIX + "同步作品",
                                    "tags": [PREFIX + "同步标签"], "plays": 123, "likes": 45,
                                    "comments": 6, "shares": 7, "cover": ""}]}

            dc.fetch_account = _fake_acc
            dc._sync_account.__globals__["fetch_account"] = _fake_acc
            aus.fetch_account_videos = _fake_videos
            res = dc.sync_one_account(DouyinAccountSyncOneIn(account_id=test_acc.id), s, test_user)
            ok("手动更新返回发布数据同步统计", res.get("ok") is True
               and res.get("videos_created") == 1 and res.get("videos_updated") == 0,
               {k: v for k, v in res.items() if k != "account"})
            ok("手动更新写入发布数据", s.query(DouyinImport).filter(
                DouyinImport.video_id == vid, DouyinImport.account_id == test_acc.id).count() == 1)
            ok("手动更新同时写账号快照", s.query(PublishAccountSnapshot).filter(
                PublishAccountSnapshot.account_id == test_acc.id).count() == before_snap + 1)
            snap_latest = s.query(PublishAccountSnapshot).filter(
                PublishAccountSnapshot.account_id == test_acc.id).order_by(
                PublishAccountSnapshot.id.desc()).first()
            ok("快照备注含发布数据同步信息", "同步发布数据" in (snap_latest.note or ""), snap_latest.note)
            # 清理本段测试写入的发布数据
            s.query(DouyinImport).filter(DouyinImport.video_id == vid).delete()
            s.commit()
        s.close()
    except Exception as exc:
        ok("账号更新总入口进程内验证", False, str(exc))

    print("\n=== 清理 ===")
    cleanup()

    print("\n=== 汇总 ===")
    print("PASS=%s FAIL=%s TOTAL=%s" % (PASS, FAIL, PASS + FAIL))
    if FAIL:
        print("失败项：")
        for status, label, extra in DETAILS:
            if status == "FAIL":
                print("  - %s | %s" % (label, extra))
    return FAIL


if __name__ == "__main__":
    try:
        code = run()
        sys.exit(1 if code else 0)
    except Exception as e:
        import traceback
        traceback.print_exc()
        print("\n测试脚本异常，尝试清理...")
        try:
            cleanup()
        except Exception:
            pass
        sys.exit(2)
