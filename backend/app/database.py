import json
import logging
import os
from datetime import datetime

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import declarative_base, sessionmaker

# 应用根目录与上传目录：供静态挂载和上传接口共用，避免路径不一致
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
UPLOAD_DIR = os.path.join(BASE_DIR, "uploads")

# 数据库路径：默认落在 backend/ 下（与 BASE_DIR 同层），不再依赖进程工作目录；
# 迁移部署时可用 AVM_DB_PATH 环境变量指定绝对路径，避免从错误目录启动连到空库。
_db_path = os.environ.get("AVM_DB_PATH", "").strip()
if not _db_path:
    _db_path = os.path.join(BASE_DIR, "ai_video_assets.db")
else:
    _db_path = os.path.abspath(_db_path)
SQLALCHEMY_DATABASE_URL = "sqlite:///" + _db_path.replace("\\", "/")

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False, "timeout": 30},
)


@event.listens_for(engine, "connect")
def _sqlite_pragmas(dbapi_conn, _record):
    """WAL + 忙等待：避免采集/审计/页面并发写入时出现 database is locked。"""
    cur = dbapi_conn.cursor()
    try:
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.execute("PRAGMA busy_timeout=30000")
    finally:
        cur.close()


SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _table_exists(conn, name: str) -> bool:
    row = conn.exec_driver_sql(
        "SELECT name FROM sqlite_master WHERE type='table' AND name=?", (name,)
    ).fetchone()
    return bool(row)


def _columns(conn, table: str):
    try:
        rows = conn.exec_driver_sql(f"PRAGMA table_info({table})").fetchall()
    except Exception:
        return []
    return [r[1] for r in rows]


def _add_column(conn, table: str, column: str, ddl: str):
    if not _table_exists(conn, table):
        return
    if column in _columns(conn, table):
        return
    conn.exec_driver_sql(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}")


def _count(conn, table: str) -> int:
    if not _table_exists(conn, table):
        return 0
    try:
        row = conn.exec_driver_sql(f"SELECT COUNT(*) FROM {table}").fetchone()
        return int(row[0]) if row else 0
    except Exception:
        return 0


def _migration_flags(conn) -> dict:
    """读取一次性迁移标记，存在 system_settings._migrations 中。"""
    if not _table_exists(conn, "system_settings"):
        return {}
    try:
        row = conn.exec_driver_sql(
            "SELECT value FROM system_settings WHERE key='_migrations'"
        ).fetchone()
        if not row or not row[0]:
            return {}
        value = row[0]
        if isinstance(value, str):
            parsed = json.loads(value)
            return parsed if isinstance(parsed, dict) else {}
        if isinstance(value, dict):
            return value
    except Exception:
        return {}
    return {}


def _migration_done(conn, key: str) -> bool:
    return bool(_migration_flags(conn).get(key))


def _mark_migration(conn, key: str) -> None:
    flags = _migration_flags(conn)
    flags[key] = True
    try:
        conn.exec_driver_sql(
            "INSERT OR REPLACE INTO system_settings (key, value, updated_at) VALUES (?, ?, ?)",
            ("_migrations", json.dumps(flags, ensure_ascii=False), datetime.now()),
        )
    except Exception as exc:  # pragma: no cover
        logging.warning("写入迁移标记失败: %s", exc)


def run_migrations():
    """轻量迁移。

    1. 旧库补字段（users 权限位等）
    2. 旧 videos 表数据迁移到 productions（保留人物绑定与时间信息）
    3. 迁移完成后移除旧 videos 相关表

    排期计划（plans）模块已下线：旧库中的空表仅保留以保证历史外键兼容，
    应用代码不再读写该表，也不会再从中回填任何业务数据。
    """
    with engine.connect() as conn:
        # ---- 1. 补字段 ----
        _add_column(conn, "users", "can_create", "BOOLEAN DEFAULT 1")
        _add_column(conn, "users", "can_view_all", "BOOLEAN DEFAULT 1")
        for table in ("videos", "characters", "categories"):
            _add_column(conn, table, "owner_id", "INTEGER")
        # 视频分类标签颜色：与制作 / 发布平台一致
        _add_column(conn, "categories", "color", "VARCHAR(20) DEFAULT '#7b62c9'")
        try:
            conn.exec_driver_sql(
                "UPDATE categories SET color = '#7b62c9' WHERE color IS NULL OR color = ''"
            )
        except Exception:
            pass
        # 视频分类：图标（上传图片 URL）与展示方式，与制作 / 发布平台同款
        _add_column(conn, "categories", "image", "VARCHAR(500) DEFAULT ''")
        _add_column(conn, "categories", "display", "VARCHAR(10) DEFAULT 'full'")
        # 创意：创作安排（优先级 + 排期日期）
        _add_column(conn, "ideas", "priority", "INTEGER DEFAULT 2")
        _add_column(conn, "ideas", "planned_at", "DATETIME")
        # 创意：创作人（负责制作视频的人，与提交人 owner_id 区分）；废弃 want_ids
        _add_column(conn, "ideas", "creator_id", "INTEGER")
        # 创意：备选标记（与流程状态独立）
        _add_column(conn, "ideas", "is_backup", "BOOLEAN DEFAULT 0")
        # 资产库：人物 / 场景 / 服装共用 characters 表，用 asset_type 区分
        _add_column(conn, "characters", "tags", "JSON")
        _add_column(conn, "characters", "updated_at", "DATETIME")
        _add_column(conn, "characters", "asset_type", "VARCHAR(20) DEFAULT 'character'")
        # 历史数据统一归为人物资产
        try:
            conn.exec_driver_sql(
                "UPDATE characters SET asset_type = 'character' "
                "WHERE asset_type IS NULL OR asset_type = ''"
            )
        except Exception:
            pass
        # 视频制作：idea_id 直接关联创意（单主线）
        _add_column(conn, "productions", "idea_id", "INTEGER")
        # 视频制作：开始时间 / 完成时间（制作时间与完成时间分列展示）
        _add_column(conn, "productions", "produced_at", "DATETIME")
        _add_column(conn, "productions", "completed_at", "DATETIME")
        # 视频制作：新增发布平台（与制作平台分开）
        _add_column(conn, "productions", "publish_platform", "VARCHAR(50) DEFAULT ''")
        # 数据中心记录状态：正常 / 隐藏 / 删除（默认正常，历史数据不受影响）
        _add_column(conn, "productions", "data_status", "VARCHAR(20) DEFAULT '正常'")
        try:
            conn.exec_driver_sql(
                "UPDATE productions SET data_status = '正常' "
                "WHERE data_status IS NULL OR data_status = ''"
            )
        except Exception:
            pass
        # 我的账号：每个抖音号独立扫码登录态与采集状态
        _add_column(conn, "publish_accounts", "sec_uid", "VARCHAR(200) DEFAULT ''")
        _add_column(conn, "publish_accounts", "douyin_profile", "VARCHAR(100) DEFAULT ''")
        _add_column(conn, "publish_accounts", "douyin_login_status", "VARCHAR(20) DEFAULT '未登录'")
        _add_column(conn, "publish_accounts", "douyin_login_at", "DATETIME")
        # 我的账号：状态 / 更新节奏 / 责任人（绑定创作者）
        _add_column(conn, "publish_accounts", "status", "VARCHAR(20) DEFAULT '正常'")
        _add_column(conn, "publish_accounts", "update_rhythm", "VARCHAR(20) DEFAULT '日更'")
        _add_column(conn, "publish_accounts", "responsible_id", "INTEGER")
        # 账号历史快照：自动更新后记录作品数 / 获赞 / 粉丝等历史指标
        if _table_exists(conn, "publish_account_snapshots"):
            # 更新前基准值：让每条快照自包含增量，首次更新也能显示变化
            _add_column(conn, "publish_account_snapshots", "prev_video_count", "INTEGER DEFAULT 0")
            _add_column(conn, "publish_account_snapshots", "prev_likes_count", "INTEGER DEFAULT 0")
            _add_column(conn, "publish_account_snapshots", "prev_followers_count", "INTEGER DEFAULT 0")
            try:
                conn.exec_driver_sql(
                    "CREATE INDEX IF NOT EXISTS ix_publish_account_snapshots_query "
                    "ON publish_account_snapshots (account_id, snapshot_at)"
                )
            except Exception:
                pass
        try:
            conn.exec_driver_sql(
                "UPDATE publish_accounts SET status = '正常' WHERE status IS NULL OR status = ''"
            )
            conn.exec_driver_sql(
                "UPDATE publish_accounts SET update_rhythm = '日更' "
                "WHERE update_rhythm IS NULL OR update_rhythm = ''"
            )
        except Exception:
            pass
        # 发布数据：记录本次快照使用的发布账号
        _add_column(conn, "publish_stats", "account", "VARCHAR(100) DEFAULT ''")
        _add_column(conn, "publish_stats", "source", "VARCHAR(20) DEFAULT 'manual'")
        # 采集写入去重：抖音作品唯一 ID
        _add_column(conn, "publish_stats", "video_id", "VARCHAR(80) DEFAULT ''")
        try:
            conn.exec_driver_sql(
                "CREATE UNIQUE INDEX IF NOT EXISTS uq_publish_stats_video_id "
                "ON publish_stats (video_id) WHERE video_id <> ''"
            )
        except Exception:
            pass
        # 账号资料：头像 / 联系方式 / 启停用 / 最近登录
        _add_column(conn, "users", "avatar", "VARCHAR(500) DEFAULT ''")
        _add_column(conn, "users", "phone", "VARCHAR(30) DEFAULT ''")
        _add_column(conn, "users", "email", "VARCHAR(100) DEFAULT ''")
        _add_column(conn, "users", "is_active", "BOOLEAN DEFAULT 1")
        _add_column(conn, "users", "last_login_at", "DATETIME")
        # 模块角色：决定可见菜单与可用按钮（超管/灵感/创作/运营）
        # 仅在首次新增该列时回填历史数据，之后由超管在「角色权限」页自由调整
        if "module_role" not in _columns(conn, "users"):
            _add_column(conn, "users", "module_role", "VARCHAR(20) DEFAULT 'production'")
            try:
                # 历史数据按原 role 映射：创作者→production，只读→operation
                conn.exec_driver_sql(
                    "UPDATE users SET module_role = 'production' WHERE role = 'creator'"
                )
                conn.exec_driver_sql(
                    "UPDATE users SET module_role = 'operation' WHERE role = 'viewer'"
                )
            except Exception:
                pass
        try:
            # 超管账号恒为「超管」模块角色（与 permissions.user_module_role 的判定保持一致）
            conn.exec_driver_sql(
                "UPDATE users SET module_role = 'super' WHERE role = 'admin'"
            )
        except Exception:
            pass
        # ---- 字段对齐：封面 / 类别 / 标签 / 成片 / 发布账号 ----
        _add_column(conn, "ideas", "cover", "VARCHAR(500) DEFAULT ''")
        _add_column(conn, "ideas", "category_id", "INTEGER")
        # 创意点赞投票：投票用户 ID 列表（JSON），旧库默认空
        _add_column(conn, "ideas", "voter_ids", "JSON DEFAULT '[]'")
        # 创意「我想做」认领标记：认领用户 ID 列表（JSON），仅标记不进排期
        _add_column(conn, "ideas", "want_ids", "JSON DEFAULT '[]'")
        # 创意视频数据：喜欢 / 评论 / 收藏 / 转发
        for col in ("like_count", "comment_count", "collect_count", "share_count"):
            _add_column(conn, "ideas", col, "INTEGER DEFAULT 0")
            try:
                conn.exec_driver_sql(
                    f"UPDATE ideas SET {col} = 0 WHERE {col} IS NULL"
                )
            except Exception:
                pass
        _add_column(conn, "productions", "cover", "VARCHAR(500) DEFAULT ''")
        # 制作记录作者：手动新建时写入当前登录者；历史数据由来源计划 / 创意回填
        _add_column(conn, "productions", "author", "VARCHAR(100) DEFAULT ''")
        _add_column(conn, "productions", "tags", "JSON")
        _add_column(conn, "productions", "douyin_url", "VARCHAR(500) DEFAULT ''")
        _add_column(conn, "productions", "video_file", "VARCHAR(500) DEFAULT ''")
        _add_column(conn, "productions", "publish_account_id", "INTEGER")
        try:
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_productions_publish_account_id "
                "ON productions (publish_account_id)"
            )
        except Exception:
            pass
        # 操作日志：新增人类可读描述字段
        _add_column(conn, "operation_logs", "summary", "VARCHAR(300) DEFAULT ''")

        # 抖音采集作品直接显示在发布数据表：记录状态字段与话题标签
        _add_column(conn, "douyin_imports", "data_status", "VARCHAR(20) DEFAULT '正常'")
        _add_column(conn, "douyin_imports", "tags", "JSON DEFAULT '[]'")

        # 抖音作品待匹配池：按作品 ID 去重索引（表由 create_all 建立）
        if _table_exists(conn, "douyin_imports"):
            try:
                conn.exec_driver_sql(
                    "CREATE UNIQUE INDEX IF NOT EXISTS uq_douyin_imports_video_id "
                    "ON douyin_imports (video_id) WHERE video_id <> ''"
                )
            except Exception:
                pass

        # ---- 1b. 单主线迁移：idea.creator_id / 全流程状态 ----
        # 制作记录作者回填：只补 author 为空的历史数据，取来源创意作者
        if _table_exists(conn, "productions"):
            try:
                conn.exec_driver_sql(
                    "UPDATE productions SET author = ("
                    "  SELECT i.author FROM ideas i WHERE i.id = productions.idea_id AND i.author IS NOT NULL AND i.author <> ''"
                    ") WHERE (author IS NULL OR author = '') AND idea_id IS NOT NULL"
                )
            except Exception as exc:  # pragma: no cover
                logging.warning("制作记录回填 author 失败: %s", exc)
        # 创意创作人回填：认领人 > 提交人，保证历史数据有创作人
        if _table_exists(conn, "ideas"):
            try:
                # 兼容旧 want_ids（JSON 字符串），取第一个作为创作人
                rows = conn.exec_driver_sql(
                    "SELECT id, want_ids, owner_id FROM ideas WHERE creator_id IS NULL"
                ).fetchall()
                for r in rows:
                    creator = None
                    raw = r[1]
                    if raw:
                        try:
                            ids = json.loads(raw) if isinstance(raw, str) else raw
                            if isinstance(ids, list) and ids:
                                creator = int(ids[0])
                        except Exception:
                            creator = None
                    if creator is None:
                        creator = r[2]
                    if creator is not None:
                        conn.exec_driver_sql(
                            "UPDATE ideas SET creator_id=? WHERE id=?", (creator, r[0])
                        )
            except Exception as exc:  # pragma: no cover
                logging.warning("创意回填 creator_id 失败: %s", exc)
        # 流程状态映射到新5态：未使用 / 已排期 / 制作中 / 待发布 / 已完成
        # 「备选库」不再是状态，改为独立备选标记 is_backup；历史备选库→未使用+点亮标记
        # 先映射制作记录状态（旧：制作中/已完成/已发布 → 新：制作中/待发布/已完成）
        status_rank = {"制作中": 1, "待发布": 2, "已完成": 3}
        if _table_exists(conn, "productions"):
            try:
                rows = conn.exec_driver_sql(
                    "SELECT id, status FROM productions ORDER BY id"
                ).fetchall()
                prod_map = {
                    "制作中": "制作中",
                    "已完成": "待发布",   # 成片完成、待发布
                    "已发布": "已完成",   # 发布完成 = 全流程完成
                    "待发布": "待发布",
                }
                for r in rows:
                    new = prod_map.get(r[1] or "", r[1])
                    if new and new != r[1]:
                        conn.exec_driver_sql(
                            "UPDATE productions SET status=? WHERE id=?", (new, r[0])
                        )
            except Exception as exc:  # pragma: no cover
                logging.warning("制作记录状态迁移失败: %s", exc)
        # 再由制作记录推导创意权威状态（取最靠后阶段）
        if _table_exists(conn, "ideas"):
            try:
                # 历史「备选库」→「未使用」并点亮备选标记（一次性迁移）
                backup_ids = {
                    r[0] for r in conn.exec_driver_sql(
                        "SELECT id FROM ideas WHERE status='备选库'"
                    ).fetchall()
                }
                conn.exec_driver_sql(
                    "UPDATE ideas SET status='未使用', is_backup=1 WHERE status='备选库'"
                )
                known_statuses = ("未使用", "已排期", "制作中", "待发布", "已完成")
                rows = conn.exec_driver_sql(
                    "SELECT id, status FROM ideas ORDER BY id"
                ).fetchall()
                for r in rows:
                    iid, old_status = r[0], r[1] or "未使用"
                    # 历史备选库记录已转「未使用」，跳过后续推导
                    if iid in backup_ids:
                        continue
                    prods = conn.exec_driver_sql(
                        "SELECT status FROM productions WHERE idea_id=?", (iid,)
                    ).fetchall()
                    statuses = [p[0] for p in prods if p[0] in status_rank]
                    if statuses:
                        best = max(statuses, key=lambda s: status_rank[s])
                    elif old_status in ("制作中",):
                        best = "制作中"
                    elif old_status == "已排期":
                        best = "已排期"
                    elif old_status in ("待发布", "已完成"):
                        best = old_status
                    elif old_status == "未使用":
                        # 明确设置的「未使用」不再被 has_plan 反向推导覆盖
                        # （备选标记是纯标记，状态由用户显式控制）
                        best = "未使用"
                    else:
                        # 历史状态缺失/非法的记录统一回到「未使用」
                        best = "未使用"
                    if best != old_status:
                        conn.exec_driver_sql(
                            "UPDATE ideas SET status=? WHERE id=?", (best, iid)
                        )
                    # 进入「制作中」但没有制作记录的，补一条（历史数据），开始时间取排期日期
                    if best == "制作中" and not statuses:
                        idea_row = conn.exec_driver_sql(
                            "SELECT title, cover, tags, douyin_url, category_id, planned_at, "
                            "creator_id, owner_id, created_at FROM ideas WHERE id=?", (iid,)
                        ).fetchone()
                        if idea_row:
                            conn.exec_driver_sql(
                                "INSERT INTO productions (title, cover, tags, douyin_url, idea_id, "
                                "category_id, status, produced_at, created_at, updated_at, owner_id, "
                                "platform, prompt, data_status) "
                                "VALUES (?, ?, ?, ?, ?, ?, '制作中', ?, ?, ?, ?, '', '[]', '正常')",
                                (
                                    idea_row[0] or "", idea_row[1] or "", idea_row[2] or "[]",
                                    idea_row[3] or "", iid, idea_row[4],
                                    idea_row[5] or idea_row[8], idea_row[8], idea_row[8],
                                    idea_row[6] or idea_row[7],
                                ),
                            )
            except Exception as exc:  # pragma: no cover
                logging.warning("创意流程状态迁移失败: %s", exc)
        try:
            conn.exec_driver_sql(
                "CREATE INDEX IF NOT EXISTS ix_productions_idea_id ON productions (idea_id)"
            )
        except Exception:
            pass

        # ---- 2. 旧数据迁移 ----
        # 仅在新表为空时执行一次，避免旧 id 与新自增 id 撞车
        prods_empty = _count(conn, "productions") == 0

        if prods_empty and _table_exists(conn, "videos") and _table_exists(conn, "productions"):
            try:
                conn.exec_driver_sql(
                    """
                    INSERT INTO productions (
                        id, title, category_id, platform, status, prompt,
                        reference_url, duration, produced_at, completed_at, published_at,
                        published_url, remark, created_at, updated_at, owner_id
                    )
                    SELECT
                        id, title, category_id, '',
                        CASE
                            WHEN status = '制作中' THEN '制作中'
                            WHEN status IN ('待发布', '已发布') THEN '已完成'
                            ELSE '制作中'
                        END,
                        COALESCE(prompt, '[]'),
                        COALESCE(reference_url, ''), duration,
                        COALESCE(produced_at, created_at, CURRENT_TIMESTAMP),
                        CASE WHEN status IN ('待发布', '已发布') THEN COALESCE(published_at, CURRENT_TIMESTAMP) ELSE NULL END,
                        CASE WHEN status = '已发布' THEN COALESCE(published_at, CURRENT_TIMESTAMP) ELSE NULL END,
                        COALESCE(published_url, ''), COALESCE(remark, ''),
                        COALESCE(created_at, CURRENT_TIMESTAMP),
                        COALESCE(updated_at, CURRENT_TIMESTAMP),
                        owner_id
                    FROM videos
                    """
                )
            except Exception as exc:  # pragma: no cover
                logging.warning("迁移 videos -> productions 失败: %s", exc)

            # 人物绑定（旧 character_id 单值 → 多对多）
            if prods_empty and _table_exists(conn, "production_characters"):
                try:
                    conn.exec_driver_sql(
                        """
                        INSERT OR IGNORE INTO production_characters
                            (production_id, character_id, role, sort, created_at)
                        SELECT id, character_id, '主角', 0, COALESCE(created_at, CURRENT_TIMESTAMP)
                        FROM videos
                        WHERE character_id IS NOT NULL
                        """
                    )
                except Exception as exc:  # pragma: no cover
                    logging.warning("迁移人物绑定失败: %s", exc)

            # 发布数据
            if prods_empty and _table_exists(conn, "video_stats") and _table_exists(conn, "publish_stats"):
                try:
                    conn.exec_driver_sql(
                        """
                        INSERT INTO publish_stats
                            (production_id, plays, likes, comments, shares, recorded_at, created_at)
                        SELECT video_id, COALESCE(plays, 0), COALESCE(likes, 0),
                               COALESCE(comments, 0), 0,
                               COALESCE(recorded_at, CURRENT_TIMESTAMP),
                               COALESCE(recorded_at, CURRENT_TIMESTAMP)
                        FROM video_stats
                        """
                    )
                except Exception as exc:  # pragma: no cover
                    logging.warning("迁移 video_stats -> publish_stats 失败: %s", exc)

        conn.commit()

        # ---- 3. 发布账号：旧配置项迁移到独立表（幂等）----
        # 旧版发布账号存在 system_settings.publish_accounts 里，
        # 现在升级为独立模块 publish_accounts 表，按 (platform, account_id, name) 去重。
        try:
            row = conn.exec_driver_sql(
                "SELECT value FROM system_settings WHERE key='publish_accounts'"
            ).fetchone()
            legacy = json.loads(row[0]) if row and row[0] else []
            if isinstance(legacy, list):
                for item in legacy:
                    if not isinstance(item, dict):
                        continue
                    name = str(item.get("name") or "").strip()
                    if not name:
                        continue
                    platform = str(item.get("platform") or "抖音")
                    account_id = str(item.get("account_id") or "")
                    exists = conn.exec_driver_sql(
                        "SELECT id FROM publish_accounts WHERE name=? AND platform=? AND account_id=?",
                        (name, platform, account_id),
                    ).fetchone()
                    if exists:
                        continue
                    conn.exec_driver_sql(
                        "INSERT INTO publish_accounts "
                        "(name, platform, account_id, avatar, tags, note, video_count, "
                        "likes_count, followers_count, douyin_uid, home_url, created_at, updated_at) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            name, platform, account_id,
                            str(item.get("avatar") or ""),
                            json.dumps(item.get("tags") or [], ensure_ascii=False),
                            str(item.get("note") or ""),
                            int(item.get("video_count") or 0),
                            int(item.get("likes_count") or 0),
                            int(item.get("followers_count") or 0),
                            str(item.get("douyin_uid") or ""),
                            str(item.get("home_url") or ""),
                            datetime.now(), datetime.now(),
                        ),
                    )
        except Exception as exc:  # pragma: no cover
            logging.warning("发布账号迁移失败: %s", exc)

        # ---- 4. 清理旧表 ----
        for table in ("videos", "video_assets", "video_stats"):
            try:
                if _table_exists(conn, table):
                    conn.exec_driver_sql(f"DROP TABLE IF EXISTS {table}")
            except Exception:
                pass
        conn.commit()
