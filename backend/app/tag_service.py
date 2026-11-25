"""标签库服务：平台任意处保存的标签都会自动登记到标签表，便于全局复用。

设计要点：
1. `collect_tags` 是幂等的：同名标签只登记一次，重复调用只累加引用计数。
2. 标签名统一做「去空格 + 去除首尾 # + 长度截断」，避免 `#甜御` 与 `甜御` 变成两条。
3. `rebuild_usage_count` 在删除标签或批量改动后重算引用次数，保证标签库排序可信。
"""
from datetime import datetime
from typing import Iterable, List, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from .models import Character, Idea, Production, Tag

MAX_TAG_LEN = 40


def normalize_tag(name: str) -> str:
    """规范化标签名：去首尾空白、去掉前导 #、截断超长。"""
    text = (name or "").strip().lstrip("#＃").strip()
    if len(text) > MAX_TAG_LEN:
        text = text[:MAX_TAG_LEN]
    return text


def normalize_tags(tags: Optional[Iterable[str]]) -> List[str]:
    """批量规范化并去重（保持顺序）。"""
    out: List[str] = []
    for raw in tags or []:
        name = normalize_tag(raw)
        if name and name not in out:
            out.append(name)
    return out


def collect_tags(db: Session, tags: Optional[Iterable[str]], source: str = "auto") -> List[str]:
    """把标签登记到标签库并返回规范化后的标签列表。"""
    names = normalize_tags(tags)
    if not names:
        return []
    now = datetime.now()
    for name in names:
        row = db.query(Tag).filter(Tag.name == name).first()
        if row:
            # 已存在：更新引用次数；手工标签不因自动收集而降级
            if row.source == "manual" and source == "auto":
                continue
            row.usage_count = (row.usage_count or 0) + 1
            row.updated_at = now
        else:
            db.add(
                Tag(
                    name=name,
                    category="通用",
                    usage_count=1,
                    source=source,
                    created_at=now,
                    updated_at=now,
                )
            )
    db.flush()
    return names


def drop_tags(db: Session, tags: Optional[Iterable[str]]) -> None:
    """标签引用减少时扣减计数（最低为 0）。"""
    for name in normalize_tags(tags):
        row = db.query(Tag).filter(Tag.name == name).first()
        if row:
            row.usage_count = max(0, (row.usage_count or 0) - 1)
            row.updated_at = datetime.now()
    db.flush()


def rebuild_usage_count(db: Session) -> int:
    """按各业务表实际引用重算标签计数，返回被同步的标签总数。"""
    counter: dict = {}

    def bump(raw):
        name = normalize_tag(raw)
        if name:
            counter[name] = counter.get(name, 0) + 1

    for row in db.query(Idea).all():
        for t in row.tags or []:
            bump(t)
    for row in db.query(Production).all():
        for t in row.tags or []:
            bump(t)
    for row in db.query(Character).all():
        for t in row.tags or []:
            bump(t)

    rows = db.query(Tag).all()
    # 用逐条 SQL 更新而非 ORM 批量 flush：多请求并发删除标签时，
    # ORM 的 synchronize_session 会因行数变化抛 StaleDataError（500）。
    now = datetime.now()
    for row in rows:
        db.execute(
            text("UPDATE tags SET usage_count = :count, updated_at = :now WHERE name = :name"),
            {"count": counter.get(row.name, 0), "now": now, "name": row.name},
        )
    db.expire_all()
    return len(rows)
