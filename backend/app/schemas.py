from datetime import datetime
from typing import Any, List, Optional

from pydantic import BaseModel, ConfigDict


# ---------- 用户与鉴权 ----------
class RegisterIn(BaseModel):
    username: str
    password: str
    nickname: str = ""


class LoginIn(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    username: str
    nickname: str = ""
    role: str = "user"
    can_create: bool = True
    can_view_all: bool = True
    module_role: str = "production"
    avatar: str = ""
    phone: str = ""
    email: str = ""
    is_active: bool = True
    last_login_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class TokenOut(BaseModel):
    token: str
    user: UserOut


# ---------- 用户管理（管理员） ----------
class UserCreateIn(BaseModel):
    username: str
    password: str
    nickname: str = ""
    role: str = "creator"
    can_create: bool = True
    can_view_all: bool = True
    module_role: str = "production"
    phone: str = ""
    email: str = ""


class UserUpdateIn(BaseModel):
    nickname: Optional[str] = None
    role: Optional[str] = None
    can_create: Optional[bool] = None
    can_view_all: Optional[bool] = None
    module_role: Optional[str] = None
    is_active: Optional[bool] = None
    phone: Optional[str] = None
    email: Optional[str] = None


# ---------- 角色权限 ----------
class RolePermissionOut(BaseModel):
    key: str
    name: str = ""
    desc: str = ""
    builtin: bool = True
    menus: List[str] = []
    buttons: List[str] = []


class RolePermissionUpdateIn(BaseModel):
    name: Optional[str] = None
    desc: Optional[str] = None
    menus: Optional[List[str]] = None
    buttons: Optional[List[str]] = None


class RoleAssignIn(BaseModel):
    module_role: str = "production"


class UserListItem(UserOut):
    plan_count: int = 0
    production_count: int = 0
    character_count: int = 0


class PasswordResetIn(BaseModel):
    new_password: str


# ---------- 个人中心 ----------
class ProfileIn(BaseModel):
    nickname: str = ""
    phone: str = ""
    email: str = ""


class PasswordChangeIn(BaseModel):
    old_password: str
    new_password: str


class AvatarIn(BaseModel):
    avatar: str = ""


# ---------- 系统配置 ----------
class SettingOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    key: str
    # 允许 list（如平台 / 发布账号选项）与 dict 两类配置值
    value: Any = {}
    updated_at: Optional[datetime] = None


class SettingUpdateIn(BaseModel):
    key: str
    value: Any = {}



# ---------- 分类 ----------
class CategoryIn(BaseModel):
    name: str
    color: str = "#7b62c9"
    image: str = ""
    display: str = "full"
    sort: int = 0


class CategoryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str = "#7b62c9"
    image: str = ""
    display: str = "full"
    sort: int


# ---------- 人物形象 ----------
class CharacterImageIn(BaseModel):
    file_path: str
    sort: int = 0


class CharacterImageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    file_path: str
    sort: int


class CharacterIn(BaseModel):
    name: str
    asset_type: str = "character"  # character 人物 / scene 场景 / costume 服装
    description: str = ""
    tags: List[str] = []
    images: List[CharacterImageIn] = []


class CharacterPatchIn(BaseModel):
    """人物资产卡片内局部编辑：只改名称或备注，不动图片与标签。"""
    name: Optional[str] = None
    description: Optional[str] = None


class CharacterOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    asset_type: str = "character"
    description: str
    tags: List[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class CharacterDetailOut(CharacterOut):
    images: List[CharacterImageOut] = []
    production_count: int = 0
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    is_owner: bool = False


# ---------- 素材共享：自定义素材库 ----------
class MaterialLibraryIn(BaseModel):
    name: str
    color: str = "#4a7cc4"
    sort: int = 0


class MaterialLibraryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    color: str = "#4a7cc4"
    sort: int = 0
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    is_owner: bool = False
    material_count: int = 0
    usage_count: int = 0  # 被制作记录引用次数，供「共享」提示


class MaterialIn(BaseModel):
    name: str
    description: str = ""
    tags: List[str] = []
    images: List[dict] = []


class MaterialPatchIn(BaseModel):
    """素材卡片内局部编辑 / 跨库移动：非空字段才更新。"""
    name: Optional[str] = None
    description: Optional[str] = None
    library_id: Optional[int] = None


class MaterialOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    library_id: int
    library_name: str = ""
    name: str
    description: str = ""
    tags: List[str] = []
    images: List[dict] = []
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    is_owner: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


# ---------- 标签库 ----------
class TagIn(BaseModel):
    name: str
    category: str = "通用"
    source: str = "manual"


class TagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    category: str = "通用"
    usage_count: int = 0
    source: str = "manual"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class TagOptionOut(BaseModel):
    """给前端下拉用的轻量标签。"""

    name: str
    category: str = "通用"
    usage_count: int = 0


# ---------- 发布账号 ----------
class PublishAccountIn(BaseModel):
    # name 允许缺省以支持「部分更新」，创建时由路由层校验非空
    name: str = ""
    platform: str = "抖音"
    account_id: str = ""
    avatar: str = ""
    tags: List[str] = []
    note: str = ""
    video_count: int = 0
    likes_count: int = 0
    followers_count: int = 0
    douyin_uid: str = ""
    sec_uid: str = ""
    home_url: str = ""
    status: str = "正常"
    update_rhythm: str = "日更"
    responsible_id: Optional[int] = None


class PublishAccountOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    platform: str = "抖音"
    account_id: str = ""
    avatar: str = ""
    tags: List[str] = []
    note: str = ""
    video_count: int = 0
    likes_count: int = 0
    followers_count: int = 0
    douyin_uid: str = ""
    sec_uid: str = ""
    home_url: str = ""
    douyin_profile: str = ""
    douyin_login_status: str = "未登录"
    douyin_login_at: Optional[datetime] = None
    status: str = "正常"
    update_rhythm: str = "日更"
    responsible_id: Optional[int] = None
    responsible_name: Optional[str] = None
    last_synced_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    # 相对上一次采集快照的增量（当前值 - 上次快照值），无历史快照时为 None
    deltas: Optional[dict] = None


# ---------- 我的账号：自动更新历史快照 ----------
class AccountSnapshotOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    account_id: int
    account_name: Optional[str] = ""
    avatar: Optional[str] = ""
    douyin_uid: Optional[str] = ""
    sec_uid: Optional[str] = ""
    video_count: Optional[int] = 0
    likes_count: Optional[int] = 0
    followers_count: Optional[int] = 0
    prev_video_count: Optional[int] = 0
    prev_likes_count: Optional[int] = 0
    prev_followers_count: Optional[int] = 0
    fetched_video_count: Optional[int] = 0
    source: Optional[str] = "auto"
    note: Optional[str] = ""
    snapshot_at: Optional[datetime] = None
    created_at: Optional[datetime] = None


class AutoUpdateRunIn(BaseModel):
    account_ids: Optional[List[int]] = None
    force: bool = False


class AutoUpdateRunOut(BaseModel):
    ok: bool = True
    message: str = ""
    total: int = 0
    updated: int = 0
    offline: int = 0
    failed: int = 0
    videos_created: int = 0
    videos_updated: int = 0
    ran_at: Optional[datetime] = None
    details: List[dict] = []


# ---------- 更新提醒：更新节奏 + 账号离线提醒 ----------
class UpdateReminderOut(BaseModel):
    account_id: int
    account_name: str = ""
    platform: str = ""
    avatar: str = ""
    status: str = "正常"
    update_rhythm: str = "日更"
    responsible_id: Optional[int] = None
    responsible_name: Optional[str] = None
    last_published_at: Optional[datetime] = None
    days_since: int = -1  # 距最近一次发布的天数，-1 表示从未发布
    due_in_days: int = 0  # 距离到期天数，<=0 表示已到期
    is_due: bool = False  # 是否到期需要更新
    reason: str = ""
    kind: str = "schedule"  # schedule 更新节奏 / offline 账号离线需重新扫码
    is_offline: bool = False
    action_label: str = "去排期"


# ---------- 抖音采集 ----------
class DouyinLoginIn(BaseModel):
    """扫码登录；不传 account_id 时使用公共登录态（创意解析等场景）。"""

    account_id: Optional[int] = None


class DouyinVideoAccountIn(BaseModel):
    """视频扫码 / 粘贴视频链接：解析作者后建号。"""

    url: str = ""
    channel: str = "auto"


class DouyinAccountSyncOneIn(BaseModel):
    """更新单个发布账号：重新抓取资料并回填。"""

    account_id: int


class DouyinAccountFetchIn(BaseModel):
    """按抖音号或主页链接抓取账号资料。"""

    query: str = ""  # 抖音号 / sec_uid / 主页链接
    force: bool = False  # True 忽略缓存强制重抓
    channel: str = "auto"  # auto 依次降级 / official 仅官方 / browser 仅浏览器
    account_id: Optional[int] = None  # 使用指定发布账号的独立登录态


class DouyinAccountFetchOut(BaseModel):
    ok: bool = False
    channel: str = ""  # 实际生效的采集通道
    message: str = ""
    need_login: bool = False  # 是否需要用户完成抖音扫码 / 滑块验证
    data: Optional[dict] = None


class DouyinVideosFetchIn(BaseModel):
    """按抖音号 / 主页链接批量取账号作品的播放数据。"""

    query: str = ""
    limit: int = 10
    account_id: Optional[int] = None  # 使用指定发布账号的独立登录态


class DouyinAccountVideosIn(BaseModel):
    """按已扫码登录的发布账号直接取作品列表，无需再填抖音号。"""

    account_id: int
    limit: int = 10


class DouyinVideosFetchOut(BaseModel):
    ok: bool = False
    channel: str = ""
    message: str = ""
    need_login: bool = False
    data: Optional[dict] = None


class DouyinVideosBatchIn(BaseModel):
    """按发布数据页当前账号标签批量拉取作品：全部账号或单个账号。"""

    account_ids: List[int] = []
    limit: int = 30


class DouyinAccountSyncOut(BaseModel):
    ok: bool = True
    total: int = 0
    succeeded: int = 0
    failed: List[dict] = []
    videos_created: int = 0
    videos_updated: int = 0


class DouyinStatsFetchIn(BaseModel):
    """按作品链接抓取视频数据。"""

    url: str = ""
    production_id: Optional[int] = None
    channel: str = "auto"
    account_id: Optional[int] = None  # 使用指定发布账号的独立登录态


class DouyinStatsFetchOut(BaseModel):
    ok: bool = False
    channel: str = ""
    message: str = ""
    need_login: bool = False
    data: Optional[dict] = None


# ---------- 创意库（五步流程第 1 步） ----------
class IdeaIn(BaseModel):
    title: str = ""
    cover: str = ""
    category_id: Optional[int] = None
    douyin_url: str = ""
    video_id: str = ""
    share_text: str = ""
    author: str = ""
    tags: List[str] = []
    remark: str = ""
    # 视频数据：播放 / 喜欢 / 评论 / 收藏 / 转发，以及时长（秒）/ 发布时间
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    collect_count: int = 0
    share_count: int = 0
    duration: Optional[float] = None
    published_at: Optional[datetime] = None
    # 创作安排：创作人（负责制作）、优先级（1 高 / 2 中 / 3 低）与排期日期
    creator_id: Optional[int] = None
    priority: int = 2
    planned_at: Optional[datetime] = None
    # 备选标记（与流程状态独立）
    is_backup: bool = False


class IdeaCommentIn(BaseModel):
    content: str = ""


class IdeaCommentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    idea_id: int
    user_id: int
    user_name: str = ""
    content: str = ""
    created_at: Optional[datetime] = None
    is_owner: bool = False


class ScheduleIn(BaseModel):
    """创意排期：直接在创意上设置排期信息，不生成独立计划记录。"""
    title: str = ""
    category_id: Optional[int] = None
    priority: int = 2
    planned_at: Optional[datetime] = None
    remark: str = ""


class IdeaOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    cover: str = ""
    category_id: Optional[int] = None
    category_name: Optional[str] = None
    douyin_url: str
    video_id: str
    share_text: str
    author: str
    tags: List[str]
    status: str
    remark: str
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    collect_count: int = 0
    share_count: int = 0
    duration: Optional[float] = None
    published_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


class IdeaDetailOut(IdeaOut):
    production_id: Optional[int] = None
    production_title: Optional[str] = None
    production_status: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    is_owner: bool = False
    # 点赞投票：票数 + 当前用户是否已投 + 投票人昵称（供悬浮展示）
    votes: int = 0
    voted: bool = False
    voter_names: List[str] = []
    # 投票规则：每人每天上限 + 当前用户今日已投，供前端禁用按钮与提示
    vote_daily_limit: int = 0
    vote_used_today: int = 0
    vote_exhausted: bool = False
    # 「我想做」认领标记：单人认领，仅标记不改变流程状态
    wants: int = 0
    wanted: bool = False
    want_names: List[str] = []
    # 当前用户的认领操作权限：创作角色可自助认领，超管可指定认领人
    can_want: bool = False
    can_assign: bool = False
    # 评论：系统内评论条数（详情在评论弹窗中按需拉取）
    comment_total: int = 0
    # 视频数据：喜欢 / 评论 / 收藏 / 转发
    like_count: int = 0
    comment_count: int = 0
    collect_count: int = 0
    share_count: int = 0
    # 创作安排：创作人（负责制作视频的人）、优先级与排期日期
    priority: int = 2
    planned_at: Optional[datetime] = None
    creator_id: Optional[int] = None
    creator_name: Optional[str] = None
    # 备选标记（与流程状态独立）
    is_backup: bool = False
    # 制作完成时间（取自关联制作记录，供创作计划列展示）
    completed_at: Optional[datetime] = None
    # 是否为管理员/归属人，可改状态与创作安排
    can_arrange: bool = False


# ---------- 制作视频 ----------
class PromptSeg(BaseModel):
    seg: str
    text: str = ""


class AssetIn(BaseModel):
    type: str  # cover / reference_shot / output
    file_path: str
    sort: int = 0


class AssetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    file_path: str
    sort: int


class CharacterLinkIn(BaseModel):
    character_id: int
    role: str = ""
    sort: int = 0


class CharacterLinkOut(BaseModel):
    id: int
    character_id: int
    character_name: str = ""
    character_cover: Optional[str] = None
    role: str = ""
    sort: int = 0


class ProductionIn(BaseModel):
    title: str = ""
    cover: str = ""
    author: str = ""
    tags: List[str] = []
    douyin_url: str = ""
    video_file: str = ""
    idea_id: Optional[int] = None
    category_id: Optional[int] = None
    platform: str = ""
    publish_platform: str = ""
    publish_account_id: Optional[int] = None
    owner_id: Optional[int] = None
    status: str = "制作中"
    prompt: List[PromptSeg] = []
    reference_url: str = ""
    duration: Optional[float] = None
    produced_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    published_at: Optional[datetime] = None
    published_url: str = ""
    remark: str = ""
    characters: List[CharacterLinkIn] = []
    assets: List[AssetIn] = []


class ProductionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    cover: str = ""
    author: str = ""
    tags: List[str] = []
    douyin_url: str = ""
    video_file: str = ""
    idea_id: Optional[int] = None
    category_id: Optional[int]
    platform: str
    publish_platform: str = ""
    publish_account_id: Optional[int] = None
    publish_account_name: Optional[str] = None
    status: str
    data_status: str = "正常"
    prompt: List[PromptSeg]
    reference_url: str
    duration: Optional[float]
    produced_at: Optional[datetime]
    completed_at: Optional[datetime]
    published_at: Optional[datetime]
    published_url: str
    remark: str
    created_at: Optional[datetime]
    updated_at: Optional[datetime]


class ProductionDetailOut(ProductionOut):
    idea_title: Optional[str] = None
    idea_douyin_url: Optional[str] = None
    category_name: Optional[str] = None
    characters: List[CharacterLinkOut] = []
    assets: List[AssetOut] = []
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    is_owner: bool = False


class ProductionListItem(ProductionOut):
    idea_title: Optional[str] = None
    idea_douyin_url: Optional[str] = None
    category_name: Optional[str] = None
    characters: List[CharacterLinkOut] = []
    cover_path: Optional[str] = None
    output_path: Optional[str] = None
    owner_id: Optional[int] = None
    owner_name: Optional[str] = None
    is_owner: bool = False


class ProductionListOut(BaseModel):
    items: List[ProductionListItem]
    total: int


# ---------- 发布数据 ----------
class PublishStatIn(BaseModel):
    production_id: int
    plays: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    account: str = ""
    source: str = "manual"
    video_id: str = ""  # 抖音作品唯一 ID，采集写入据此去重
    recorded_at: Optional[datetime] = None


class PublishStatBatchIn(BaseModel):
    """批量写入数据快照：抖音作品采集后一次提交多条。"""

    items: List[PublishStatIn] = []


class PublishStatBatchOut(BaseModel):
    ok: bool = True
    created: int = 0
    updated: int = 0
    skipped: int = 0
    message: str = ""


class DouyinImportVideoIn(BaseModel):
    """从抖音采集作品导入成已发布视频时，单条作品的数据。"""

    video_id: str = ""          # 抖音作品唯一 ID，去重依据
    title: str = ""
    cover: str = ""
    tags: List[str] = []        # 作品描述中的话题标签
    plays: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    create_time: Optional[int] = None   # 作品发布时间（秒级时间戳）
    account_id: Optional[int] = None    # 归属的发布账号
    account_name: str = ""
    data_status: str = "正常"           # 正常 / 隐藏 / 删除（隐藏作品手工录入时用）


class DouyinImportIn(BaseModel):
    videos: List[DouyinImportVideoIn] = []


class DouyinImportOut(BaseModel):
    ok: bool = True
    created: int = 0
    updated: int = 0
    skipped: int = 0
    message: str = ""


class DouyinImportItemOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    video_id: str = ""
    title: str = ""
    cover: str = ""
    tags: List[str] = []
    plays: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    create_time: Optional[int] = None
    account_id: Optional[int] = None
    account_name: str = ""
    status: str = "待匹配"
    data_status: str = "正常"
    production_id: Optional[int] = None
    production_title: str = ""
    created_at: Optional[datetime] = None
    matched_at: Optional[datetime] = None


class DouyinImportUpdate(BaseModel):
    """发布数据表格内直接编辑抖音采集行的数据。"""

    plays: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    account_name: str = ""


class DouyinImportMatchIn(BaseModel):
    """手动把某条待匹配作品关联到一条创作记录。"""
    production_id: int


class PublishStatUpdate(BaseModel):
    """数据中心「编辑」：只更新显式传入的字段。"""

    plays: int = 0
    likes: int = 0
    comments: int = 0
    shares: int = 0
    account: str = ""
    recorded_at: Optional[datetime] = None


class PublishStatOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    production_id: int
    plays: int
    likes: int
    comments: int
    shares: int
    account: str = ""
    source: str = "manual"
    video_id: str = ""
    recorded_at: Optional[datetime]


class DataStatusUpdate(BaseModel):
    """数据中心记录状态切换：正常 / 隐藏 / 删除。"""

    status: str = "正常"


class StatusUpdate(BaseModel):
    """表格内点击状态标签直接切换状态。"""

    status: str


class IdeaArrangeIn(BaseModel):
    """创作安排弹窗：状态 + 创作人 + 优先级 + 排期日期 一次提交。
    字段缺省（未出现在请求体）表示保持原值；显式传 null 表示清空。
    """
    status: Optional[str] = None
    creator_id: Optional[int] = None
    priority: Optional[int] = None
    planned_at: Optional[datetime] = None


# ---------- 链接解析 ----------
class ShareTextIn(BaseModel):
    text: str = ""
    # 是否在解析链接后自动抓取作者/封面/视频数据（可关闭以加快纯文案解析）
    auto_fetch: bool = True


class ParseResultOut(BaseModel):
    title: str = ""
    url: str = ""
    raw_url: str = ""
    video_id: str = ""
    author: str = ""
    author_id: str = ""
    cover: str = ""
    tags: List[str] = []
    play_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    collect_count: int = 0
    share_count: int = 0
    duration: Optional[float] = None
    published_at: Optional[datetime] = None
    # auto = 自动抓取成功；manual = 需手工填写（未抓取或失败）
    fetch_status: str = ""
    raw: str = ""
    resolved: bool = False
    title_from_text: bool = False
    message: str = ""


# ---------- 概览 ----------
class OverviewOut(BaseModel):
    idea_total: int = 0
    idea_unused: int = 0
    idea_scheduled: int = 0
    plan_total: int = 0
    plan_pending: int = 0
    plan_in_progress: int = 0
    plan_done: int = 0
    production_total: int = 0
    production_making: int = 0
    production_done: int = 0
    production_published: int = 0
    character_total: int = 0
    asset_total: int = 0
    scene_total: int = 0
    costume_total: int = 0
    plays_total: int = 0
    likes_total: int = 0
    comments_total: int = 0
    shares_total: int = 0
    published_this_month: int = 0
    mine: dict = {}
