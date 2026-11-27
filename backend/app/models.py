from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import relationship

from .database import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    password_hash = Column(String(200), nullable=False)
    nickname = Column(String(50), default="")
    role = Column(String(10), default="user")  # admin 超管 / creator 创作者 / viewer 只读
    # 权限位：admin 全权；creator 可创建并管理自己的资产；viewer 只读
    can_create = Column(Boolean, default=True)
    can_view_all = Column(Boolean, default=True)
    # 模块角色：决定可见菜单与可用按钮（超管/灵感/创作/运营），详见 permissions.py
    module_role = Column(String(20), default="production", index=True)
    # 账号资料
    avatar = Column(String(500), default="")  # 头像文件路径
    phone = Column(String(30), default="")
    email = Column(String(100), default="")
    is_active = Column(Boolean, default=True)  # 停用后禁止登录
    last_login_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.now)

    @property
    def display_name(self) -> str:
        return self.nickname or self.username

    @property
    def is_admin(self) -> bool:
        return self.role == "admin"


class SystemSetting(Base):
    """系统配置：键值对存储，供「配置中心」页面读写。"""

    __tablename__ = "system_settings"

    id = Column(Integer, primary_key=True, index=True)
    key = Column(String(100), unique=True, nullable=False, index=True)
    value = Column(JSON, default=dict)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)


class OperationLog(Base):
    """平台操作日志：自动记录写操作（新增 / 编辑 / 删除 / 执行）。"""

    __tablename__ = "operation_logs"

    id = Column(Integer, primary_key=True, index=True)
    module = Column(String(40), default="其他", index=True)  # 业务模块
    action = Column(String(20), default="操作", index=True)  # 新增 / 编辑 / 删除 / 执行
    target = Column(String(120), default="")  # 操作对象（接口资源）
    summary = Column(String(300), default="")  # 人类可读描述：新增了「分类」等
    method = Column(String(10), default="")
    path = Column(String(300), default="")
    username = Column(String(60), default="")  # 操作人显示名
    user_id = Column(Integer, nullable=True, index=True)
    status_code = Column(Integer, default=200)
    ip = Column(String(60), default="")
    created_at = Column(DateTime, default=datetime.now, index=True)


class Tag(Base):
    """标签库：全局标签字典。

    平台任意处保存的标签都会自动登记到这里，便于其它地方调用与复用。
    """

    __tablename__ = "tags"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False, index=True)  # 标签名（去重键）
    category = Column(String(30), default="通用", index=True)  # 分类：通用/题材/风格/人物/场景/服装
    usage_count = Column(Integer, default=0)  # 被引用次数，用于排序与清理冷门标签
    source = Column(String(30), default="manual")  # manual 手工 / auto 自动收集
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)


class PublishAccount(Base):
    """发布账号：视频实际发布到哪个抖音/小红书账号（独立模块）。

    video_count 作品数 / likes_count 获赞 / followers_count 粉丝
    """

    __tablename__ = "publish_accounts"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False, index=True)  # 账号名称
    platform = Column(String(50), default="抖音", index=True)  # 发布平台
    account_id = Column(String(100), default="", index=True)  # 平台内账号 ID / 抖音号
    avatar = Column(String(500), default="")  # 头像
    tags = Column(JSON, default=list)  # 账号标签
    note = Column(Text, default="")
    # ---- 抖音数据（可由采集通道自动回填，也可手工填写）----
    video_count = Column(Integer, default=0)  # 视频数量 / 作品数
    likes_count = Column(Integer, default=0)  # 获赞（总赞）
    followers_count = Column(Integer, default=0)  # 粉丝数
    douyin_uid = Column(String(100), default="", index=True)  # 抖音号
    sec_uid = Column(String(200), default="", index=True)  # 抖音 sec_uid
    home_url = Column(String(500), default="")  # 主页链接
    # 每个账号独立保存扫码登录态（Playwright 持久化目录标识），互不干扰
    douyin_profile = Column(String(100), default="", index=True)
    douyin_login_status = Column(String(20), default="未登录")  # 未登录 / 已登录 / 需验证
    douyin_login_at = Column(DateTime, nullable=True)  # 最近一次扫码登录时间
    last_synced_at = Column(DateTime, nullable=True)  # 最近一次采集时间
    # ---- 运营维护字段 ----
    status = Column(String(20), default="正常", index=True)  # 正常 / 搁置 / 废弃
    update_rhythm = Column(String(20), default="日更", index=True)  # 日更 / 隔日更 / 周更
    responsible_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)  # 责任人（绑定创作者）
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", foreign_keys=[owner_id])
    responsible = relationship("User", foreign_keys=[responsible_id])


class PublishAccountSnapshot(Base):
    """我的账号：每次自动 / 手动更新后的历史数据快照。

    记录账号资料里展示的作品数量、获赞、粉丝等指标；发布数据作品的
    播放 / 点赞 / 评论 / 转发更新不写这里，仍按 video_id 留在发布数据表。
    """

    __tablename__ = "publish_account_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("publish_accounts.id"), nullable=False, index=True)
    account_name = Column(String(100), default="")
    avatar = Column(String(500), default="")
    douyin_uid = Column(String(100), default="")
    sec_uid = Column(String(200), default="")
    video_count = Column(Integer, default=0)      # 作品数量（更新后）
    likes_count = Column(Integer, default=0)      # 获赞（更新后）
    followers_count = Column(Integer, default=0)  # 粉丝（更新后）
    # 更新前的值：快照自包含增量基准，首次更新也能算出变化量
    prev_video_count = Column(Integer, default=0)
    prev_likes_count = Column(Integer, default=0)
    prev_followers_count = Column(Integer, default=0)
    fetched_video_count = Column(Integer, default=0)  # 本次实际采集到的作品条数
    source = Column(String(20), default="auto")   # auto 定时任务 / manual 手动更新
    note = Column(String(300), default="")
    snapshot_at = Column(DateTime, default=datetime.now, index=True)
    created_at = Column(DateTime, default=datetime.now)

    account = relationship("PublishAccount")


class Category(Base):
    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(50), unique=True, nullable=False)
    color = Column(String(20), default="#7b62c9")  # 标签颜色，与制作/发布平台一致
    # 图标（上传图片 URL）与展示方式，与制作 / 发布平台同款，作用到全局
    image = Column(String(500), default="")
    display = Column(String(10), default="full")  # full 全显 / label 标签 / icon 图标
    sort = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    productions = relationship("Production", back_populates="category")
    owner = relationship("User")


class MaterialLibrary(Base):
    """素材共享：可自定义的素材库标签（人物库 / 服装库 / 场景库…）。"""

    __tablename__ = "material_libraries"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(80), unique=True, nullable=False, index=True)
    color = Column(String(20), default="#4a7cc4")
    sort = Column(Integer, default=0)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    owner = relationship("User")


class Material(Base):
    """素材共享：归属于某个自定义素材库的共享素材（图片 + 标签）。"""

    __tablename__ = "materials"

    id = Column(Integer, primary_key=True, index=True)
    library_id = Column(Integer, ForeignKey("material_libraries.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, default="")
    tags = Column(JSON, default=list)
    images = Column(JSON, default=list)  # [{"file_path": "...", "sort": 0}]
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)

    library = relationship("MaterialLibrary")
    owner = relationship("User")


class VoteRecord(Base):
    """创意投票记录：记录投票时间，用于「每人每天投票次数上限」规则。

    active=True 表示当前有效的一票；取消投票后置为 False 并同步 ideas.voter_ids。
    """

    __tablename__ = "vote_records"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

    idea = relationship("Idea")
    user = relationship("User")


class Character(Base):
    """资产库：人物 / 场景 / 服装三类资产共用一张表，图片为主，可被制作记录引用。

    asset_type: character 人物资产 / scene 场景资产 / costume 服装资产
    """

    __tablename__ = "characters"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    asset_type = Column(String(20), default="character", index=True)  # 资产类型
    description = Column(Text, default="")
    tags = Column(JSON, default=list)  # 资产标签，如 ["古装", "长发"]
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    images = relationship(
        "CharacterImage",
        back_populates="character",
        cascade="all, delete-orphan",
        order_by="CharacterImage.sort",
    )
    productions = relationship(
        "Production",
        secondary="production_characters",
        back_populates="characters",
        viewonly=True,
    )
    owner = relationship("User")


class CharacterImage(Base):
    __tablename__ = "character_images"

    id = Column(Integer, primary_key=True, index=True)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    file_path = Column(String(500), nullable=False)
    sort = Column(Integer, default=0)

    character = relationship("Character", back_populates="images")


class Idea(Base):
    """创意库：创作流程第 1 步，负责收集创意视频并承载全流程状态。

    由抖音分享链接/文案解析而来；排期信息直接记录在创意上，不再生成独立的计划表。
    状态：未使用 / 已排期 / 制作中 / 待发布 / 已完成
    """

    __tablename__ = "ideas"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), default="", nullable=False)  # 创意名称
    cover = Column(String(500), default="")  # 封面截图
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)  # 类别
    douyin_url = Column(String(500), default="", index=True)  # 抖音链接（保留原始短链）
    video_id = Column(String(50), default="", index=True)  # 抖音视频 ID，用于去重
    share_text = Column(Text, default="")  # 原始分享文案，完整保留
    author = Column(String(100), default="")  # 手动填写
    tags = Column(JSON, default=list)  # 话题标签
    voter_ids = Column(JSON, default=list)  # 点赞投票的用户 ID 列表（一人一票，可取消）
    # want_ids 已废弃，字段保留仅为兼容历史数据与接口；创作人统一用 creator_id
    want_ids = Column(JSON, default=list)
    # 创作人：负责制作视频的人（与 owner_id 提交人区分）
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    # 视频数据（抖音侧抓取或手工录入）：播放 / 喜欢 / 评论 / 收藏 / 转发
    play_count = Column(Integer, default=0)
    like_count = Column(Integer, default=0)
    comment_count = Column(Integer, default=0)
    collect_count = Column(Integer, default=0)
    share_count = Column(Integer, default=0)
    # 视频时长（秒）与发布时间（抖音侧抓取或手工录入）
    duration = Column(Float, nullable=True)
    published_at = Column(DateTime, nullable=True)
    # 全流程权威状态：未使用 / 已排期 / 制作中 / 待发布 / 已完成
    status = Column(String(20), default="未使用", index=True)
    # 备选标记：与流程状态独立，点亮表示标记为备选（状态列前的星标）
    is_backup = Column(Boolean, default=False, index=True)
    # 创作安排：优先级（1 高 / 2 中 / 3 低）与排期日期，由状态弹窗统一设置
    priority = Column(Integer, default=2)
    planned_at = Column(DateTime, nullable=True)
    remark = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    owner = relationship("User", foreign_keys=[owner_id])
    creator = relationship("User", foreign_keys=[creator_id])
    category = relationship("Category")
    productions = relationship("Production", back_populates="idea")
    vote_records = relationship("VoteRecord", back_populates="idea", cascade="all, delete-orphan")


class IdeaComment(Base):
    """创意评论：多人可在同一条创意下发表意见。

    评论只做讨论，不影响创意状态与排期流程。
    """

    __tablename__ = "idea_comments"

    id = Column(Integer, primary_key=True, index=True)
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    content = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now, index=True)

    idea = relationship("Idea", backref="comments")
    user = relationship("User")


class Production(Base):
    """视频创作记录：创作流程第 2 步，一条记录覆盖制作到发布完成。

    状态：制作中 / 待发布 / 废弃（展示为「已废弃」）/ 已完成（展示为「已发布」）
    platform = 制作平台（硬核 / 小云雀 / 三方平台）
    publish_platform = 发布平台（抖音 / 小红书 / B站 / 视频号，配置中心维护）
    """

    __tablename__ = "productions"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(500), default="", nullable=False)
    cover = Column(String(500), default="")  # 参考视频封面
    author = Column(String(100), default="")  # 视频作者（手动新建时为当前登录者）
    tags = Column(JSON, default=list)  # 视频标签
    douyin_url = Column(String(500), default="", index=True)  # 参考视频抖音链接
    video_file = Column(String(500), default="")  # 成片文件（mp4，可在线预览）
    idea_id = Column(Integer, ForeignKey("ideas.id"), nullable=True, index=True)  # 来源创意
    category_id = Column(Integer, ForeignKey("categories.id"), nullable=True)
    platform = Column(String(30), default="")  # 制作平台
    publish_platform = Column(String(50), default="")  # 发布平台
    publish_account_id = Column(Integer, ForeignKey("publish_accounts.id"), nullable=True, index=True)
    status = Column(String(20), default="制作中", index=True)
    published_video_id = Column(String(80), default="")  # 当前绑定的发布作品唯一 ID（状态锁定依据）
    data_status = Column(String(20), default="正常", index=True)  # 数据中心记录状态：正常 / 隐藏 / 删除
    prompt = Column(JSON, default=list)  # [{"seg": "人物背景", "text": "..."}]
    reference_url = Column(String(500), default="")  # 参考视频链接
    duration = Column(Float, nullable=True)
    produced_at = Column(DateTime, nullable=True)  # 制作时间
    completed_at = Column(DateTime, nullable=True)  # 完成时间
    published_at = Column(DateTime, nullable=True)  # 发布时间
    published_url = Column(String(500), default="")  # 发布后的回链
    remark = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.now)
    updated_at = Column(DateTime, default=datetime.now, onupdate=datetime.now)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)

    idea = relationship("Idea", back_populates="productions")
    category = relationship("Category", back_populates="productions")
    publish_account = relationship("PublishAccount")
    owner = relationship("User")
    characters = relationship(
        "Character",
        secondary="production_characters",
        back_populates="productions",
        viewonly=True,
    )
    links = relationship(
        "ProductionCharacter",
        back_populates="production",
        cascade="all, delete-orphan",
        order_by="ProductionCharacter.sort",
    )
    assets = relationship(
        "ProductionAsset",
        back_populates="production",
        cascade="all, delete-orphan",
        order_by="ProductionAsset.sort",
    )
    stats = relationship(
        "PublishStat",
        back_populates="production",
        cascade="all, delete-orphan",
        order_by="PublishStat.recorded_at.desc()",
    )


class ProductionCharacter(Base):
    """制作记录 ↔ 人物形象 的绑定关系（多对多）。

    role 标注该人物在本条视频中的角色（如「主角」「配角」）。
    """

    __tablename__ = "production_characters"
    __table_args__ = (UniqueConstraint("production_id", "character_id", name="uq_production_character"),)

    id = Column(Integer, primary_key=True, index=True)
    production_id = Column(Integer, ForeignKey("productions.id"), nullable=False)
    character_id = Column(Integer, ForeignKey("characters.id"), nullable=False)
    role = Column(String(50), default="")  # 主角 / 配角 / 替身
    sort = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.now)

    production = relationship("Production", back_populates="links")
    character = relationship("Character")


class ProductionAsset(Base):
    """制作附件：type = cover 封面 / reference_shot 参考截图 / output 成片"""

    __tablename__ = "production_assets"

    id = Column(Integer, primary_key=True, index=True)
    production_id = Column(Integer, ForeignKey("productions.id"), nullable=False)
    type = Column(String(30), nullable=False)
    file_path = Column(String(500), nullable=False)
    sort = Column(Integer, default=0)

    production = relationship("Production", back_populates="assets")


class PublishStat(Base):
    """发布数据：播放 / 点赞 / 评论 / 转发，按时间留痕可追增长。"""

    __tablename__ = "publish_stats"

    id = Column(Integer, primary_key=True, index=True)
    production_id = Column(Integer, ForeignKey("productions.id"), nullable=False)
    plays = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    collects = Column(Integer, default=0)  # 收藏数（抖音作品自身采集数据）
    shares = Column(Integer, default=0)
    account = Column(String(100), default="")  # 发布账号（配置中心维护，快照时记录名称）
    source = Column(String(20), default="manual")  # manual 手工录入 / auto 自动采集
    video_id = Column(String(80), default="", index=True)  # 抖音作品唯一 ID，采集写入去重依据
    recorded_at = Column(DateTime, default=datetime.now, index=True)
    created_at = Column(DateTime, default=datetime.now)

    production = relationship("Production", back_populates="stats")


class DouyinImport(Base):
    """抖音采集作品的待匹配池：导入后不直接发布，等用户在表格里手动关联创作记录。"""

    __tablename__ = "douyin_imports"

    id = Column(Integer, primary_key=True, index=True)
    video_id = Column(String(80), default="", index=True)  # 抖音作品唯一 ID，导入去重依据
    title = Column(String(500), default="")
    cover = Column(String(500), default="")
    tags = Column(JSON, default=list)  # 作品描述里的话题标签
    plays = Column(Integer, default=0)
    likes = Column(Integer, default=0)
    comments = Column(Integer, default=0)
    collects = Column(Integer, default=0)  # 收藏数（抖音作品自身采集数据）
    shares = Column(Integer, default=0)
    create_time = Column(Integer, nullable=True)  # 作品发布时间（秒级时间戳）
    duration = Column(Float, nullable=True)  # 作品时长（秒，抖音视频自身数据）
    account_id = Column(Integer, nullable=True)
    account_name = Column(String(100), default="")
    status = Column(String(20), default="待匹配", index=True)  # 待匹配 / 已匹配
    data_status = Column(String(20), default="正常", index=True)  # 数据中心记录状态：正常 / 隐藏 / 删除
    production_id = Column(Integer, nullable=True)  # 匹配到的创作记录
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.now)
    matched_at = Column(DateTime, nullable=True)

    owner = relationship("User")


# ---------- 兼容旧表（历史数据迁移用） ----------
class LegacyVideo(Base):
    """旧 videos 表的结构快照，仅用于一次性迁移。"""

    __tablename__ = "videos"

    id = Column(Integer, primary_key=True)
    title = Column(String(500))
    author = Column(String(100))
    tags = Column(JSON)
    douyin_share_text = Column(Text)
    douyin_short_url = Column(String(500))
    category_id = Column(Integer)
    character_id = Column(Integer)
    reference_url = Column(String(500))
    duration = Column(Float)
    prompt = Column(JSON)
    status = Column(String(20))
    produced_at = Column(DateTime)
    published_at = Column(DateTime)
    published_url = Column(String(500))
    remark = Column(Text)
    created_at = Column(DateTime)
    updated_at = Column(DateTime)
    owner_id = Column(Integer)
