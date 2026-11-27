<template>
  <div class="stack">
    <PageHeader
      :icon="Collection"
      title="创意灵感"
      tone="blue"
      desc="第一步 · 收集灵感素材：封面截图、名称、类别与话题标签；设置创作计划后进入视频创作"
    >
      <template #extra>
        <el-input
          v-model="keyword"
          placeholder="搜索名称 / 作者 / 链接"
          clearable
          style="width: 190px"
        >
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="usage" style="width: 108px">
          <el-option v-for="u in USAGE_FILTER_OPTIONS" :key="u.value" :label="u.label" :value="u.value" />
        </el-select>
        <el-select v-model="scope" style="width: 118px" @change="load">
          <el-option value="all" label="全部成员" />
          <el-option value="mine" label="我的创意" />
          <el-option value="planned" label="我的计划" />
        </el-select>
        <el-button v-if="perm.can('ideas.create')" type="primary" :icon="Plus" @click="openCreate">收集创意</el-button>
      </template>
    </PageHeader>

    <!-- 创意概览：统计基于当前可见范围的全部创意，不受筛选条件影响 -->
    <div class="stat-row">
      <StatCard
        v-for="s in statCards"
        :key="s.label"
        :label="s.label"
        :value="s.value"
        :icon="s.icon"
        :tone="s.tone"
      />
    </div>

    <el-card shadow="never" class="adm-card adm-card--table" :class="{ 'is-loading': loading }">
      <GridSkeleton v-if="loading" :rows="8" :cols="6" />
      <div class="adm-table-wrap">
        <el-table :data="pagedList" stripe style="width: 100%" empty-text="还没有创意，点右上角「收集创意」开始">
          <el-table-column label="封面" width="88" align="center">
            <template #default="{ row }">
              <div class="adm-cell-cover">
                <img v-if="row.cover" :src="row.cover" class="adm-cover-thumb" :alt="row.title" />
                <img v-else src="/placeholder.svg" class="adm-cover-thumb is-empty" alt="暂无封面" />
              </div>
            </template>
          </el-table-column>

          <!-- 视频名称：点击跳转抖音；第二行展示作者（无作者显示 @未获取）与类别 -->
          <el-table-column label="视频名称" min-width="190" align="left">
            <template #default="{ row }">
              <a
                v-if="row.douyin_url"
                :href="row.douyin_url"
                target="_blank"
                rel="noopener"
                class="adm-cell-link adm-cell-text adm-cell-text--clamp2"
                :title="(row.title || '未命名创意') + ' · 点击打开抖音'"
              >{{ row.title || '未命名创意' }}</a>
              <span v-else class="adm-cell-text adm-cell-text--clamp2" :title="row.title || '未命名创意'">
                {{ row.title || '未命名创意' }}
              </span>
              <div class="adm-cell-sub">
                <span class="idea-author" :title="row.author || '未获取作者'">@{{ row.author || '未获取' }}</span>
                <OptionBadge
                  v-if="row.category_name"
                  :name="row.category_name"
                  :color="settings.option('category', row.category_name).color"
                  :image="settings.option('category', row.category_name).image"
                  :display="settings.option('category', row.category_name).display"
                  class="idea-cat"
                />
                <span v-else class="adm-cell-empty">—</span>
              </div>
              <!-- 视频元信息：第三行显示发布时间 + 时长（解析回填，小字） -->
              <div class="idea-video-meta">
                <span class="idea-meta-item" :title="row.published_at ? '发布时间：' + formatDateTime(row.published_at) : '未获取发布时间'">
                  <el-icon :size="11"><Calendar /></el-icon>
                  {{ row.published_at ? formatDate(row.published_at) : '—' }}
                </span>
                <span class="idea-meta-sep">·</span>
                <span class="idea-meta-item" :title="row.duration != null ? '视频时长：' + Number(row.duration).toFixed(1) + 'S' : '未获取时长'">
                  <SocialIcon name="duration" :size="11" />
                  {{ row.duration != null ? Number(row.duration).toFixed(1) + 'S' : '—' }}
                </span>
              </div>
            </template>
          </el-table-column>

          <!-- 话题标签：最多三行，溢出显示 +N，悬浮展示剩余标签 -->
          <el-table-column label="话题标签" min-width="136" align="left">
            <template #default="{ row }">
              <TagCell :tags="row.tags || []" :max-lines="3" />
            </template>
          </el-table-column>

          <!-- 视频数据：喜欢 / 评论 / 收藏 / 转发（两行两列） -->
          <el-table-column label="视频数据" min-width="128" align="center">
            <template #default="{ row }">
              <div class="video-stat">
                <span class="video-stat-item is-like" title="喜欢数">
                  <span class="video-stat-ico"><SocialIcon name="heart" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.like_count) }}</span>
                </span>
                <span class="video-stat-item is-comment" title="评论数">
                  <span class="video-stat-ico"><SocialIcon name="comment" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.comment_count) }}</span>
                </span>
                <span class="video-stat-item is-collect" title="收藏数">
                  <span class="video-stat-ico"><SocialIcon name="star" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.collect_count) }}</span>
                </span>
                <span class="video-stat-item is-share" title="转发数">
                  <span class="video-stat-ico"><SocialIcon name="share" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.share_count) }}</span>
                </span>
              </div>
            </template>
          </el-table-column>

          <!-- 状态：默认不显示星标；点击状态切换备选标记（点亮后显示星标，再点取消）；所有状态均可点，不改流程状态 -->
          <el-table-column label="状态" min-width="112" align="center">
            <template #default="{ row }">
              <button
                type="button"
                class="status-tag-btn"
                :class="{ 'is-backup': row.is_backup }"
                :disabled="!canEditStatus(row)"
                :title="canEditStatus(row) ? (row.is_backup ? '点击取消备选标记' : '点击标记为备选') : '仅归属人或管理员可标记'"
                @click="toggleBackup(row)"
              >
                <el-icon v-if="row.is_backup" :size="13" class="status-star-on"><Star /></el-icon>
                <el-tag :type="ideaStatusType(row.status)" size="small" effect="light">{{ ideaStatusLabel(row.status) }}</el-tag>
              </button>
            </template>
          </el-table-column>

          <!-- 创意提供：上为提交人昵称标签，下为提交时间（同宽、小字） -->
          <el-table-column label="创意提供" min-width="136" align="center">
            <template #default="{ row }">
              <div class="idea-owner-cell">
                <span class="idea-owner-tag" :title="row.owner_name || '未归属'">{{ row.owner_name || '未归属' }}</span>
                <span class="idea-owner-date adm-cell-time" :title="formatDateTime(row.created_at)">{{ formatDateTime(row.created_at) }}</span>
              </div>
            </template>
          </el-table-column>

          <!-- 创作计划：未使用显示默认图标；已排期/制作中显示优先级/创作人/制作时间（可点取消排期）；待发布/已完成只显示制作人+完成时间 -->
          <el-table-column label="创作计划" min-width="150" align="center">
            <template #default="{ row }">
              <!-- 未使用：默认图标，点击弹窗设置紧急程度 / 创作人 / 制作时间 -->
              <button
                v-if="row.status === '未使用'"
                type="button"
                class="plan-icon-btn"
                :disabled="!canEditStatus(row)"
                :title="canEditStatus(row) ? '设置创作计划（进入已排期）' : '仅归属人或管理员可设置'"
                @click="openPlan(row)"
              >
                <el-icon :size="18"><Calendar /></el-icon>
              </button>
              <!-- 已排期 / 制作中：优先级 + 创作人 + 制作时间；可点取消排期 -->
              <button
                v-else-if="['已排期', '制作中'].includes(row.status)"
                type="button"
                class="arrange-cell arrange-cell--btn"
                :class="{ 'is-cancellable': canEditStatus(row) }"
                :disabled="!canEditStatus(row)"
                :title="canEditStatus(row) ? '点击取消排期' : row.creator_name || '未指定创作人'"
                @click="openCancelPlan(row)"
              >
                <span class="arrange-priority">
                  <span class="arrange-priority-tag" :class="'is-p' + (row.priority || 2)">
                    {{ planPriorityLabel(row.priority || 2) }}
                  </span>
                </span>
                <span class="arrange-info">
                  <span class="arrange-creator-tag" :title="row.creator_name || '未指定创作人'">{{ row.creator_name || '未指定' }}</span>
                  <span class="arrange-date">{{ formatDate(row.planned_at) }}</span>
                </span>
              </button>
              <!-- 待发布 / 已完成：紧急程度 + 制作人 + 完成时间，不可点击 -->
              <div v-else class="arrange-cell arrange-cell--done">
                <span class="arrange-priority">
                  <span class="arrange-priority-tag" :class="'is-p' + (row.priority || 2)">
                    {{ planPriorityLabel(row.priority || 2) }}
                  </span>
                </span>
                <span class="arrange-info">
                  <span class="arrange-creator-tag" :title="row.creator_name || '未指定制作人'">{{ row.creator_name || '未指定' }}</span>
                  <span class="arrange-date">{{ formatDate(row.completed_at) }}</span>
                </span>
              </div>
            </template>
          </el-table-column>

          <!-- 点赞评论：点赞投票与系统评论合并为一列 -->
          <el-table-column label="点赞评论" min-width="130" align="center">
            <template #default="{ row }">
              <div class="idea-feedback-cell">
                <el-tooltip
                  :content="voteTooltip(row)"
                  placement="top"
                  :disabled="votingId === row.id"
                >
                  <button
                    type="button"
                    class="vote-btn"
                    :class="{ 'is-voted': row.voted, 'is-exhausted': isVoteExhausted(row) }"
                    :disabled="votingId === row.id"
                    :title="voteTitle(row)"
                    @click="toggleVote(row)"
                  >
                    <SocialIcon name="heart" :size="15" />
                    <span class="vote-count">{{ row.votes || 0 }}</span>
                  </button>
                </el-tooltip>
                <el-tooltip content="查看与发表评论" placement="top">
                  <button
                    type="button"
                    class="comment-btn"
                    :class="{ 'is-active': (row.comment_total || 0) > 0 }"
                    title="查看与发表评论"
                    @click="openComments(row)"
                  >
                    <el-icon :size="15"><ChatLineRound /></el-icon>
                    <span class="comment-count">{{ row.comment_total || 0 }}</span>
                  </button>
                </el-tooltip>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" min-width="120" fixed="right" align="center">
            <template #default="{ row }">
              <div class="adm-cell-actions">
                <el-button v-if="perm.can('ideas.edit') && (row.is_owner || auth.isAdmin)" type="text" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button v-if="perm.can('ideas.delete') && (row.is_owner || auth.isAdmin)" type="text" size="small" class="danger-text" @click="remove(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :image-size="100" description="还没有创意，点右上角「收集创意」开始" />
          </template>
        </el-table>
      </div>

      <AppPagination v-model:page="page" :total="filteredList.length" v-model:page-size="PAGE_SIZE" />
    </el-card>

    <!-- 收集 / 编辑弹窗 -->
    <el-dialog
      v-model="dialog.visible"
      width="640px"
      :close-on-click-modal="false"
    >
      <template #header>
        <DialogHeader
          :icon="Collection"
          :title="dialog.isEdit ? '编辑创意' : '收集创意'"
          sub="粘贴抖音链接，自动解析名称、话题标签、作者、封面与视频数据"
          tone="blue"
        />
      </template>
      <!-- 未点保存前不挂校验规则，避免子组件挂载时的空值 change 触发红框告警 -->
      <el-form
        ref="formRef"
        :model="dialog.form"
        :rules="formRules"
        label-width="88px"
        label-position="right"
      >
        <el-form-item label="抖音链接" prop="douyin_url" required>
          <el-input v-model="dialog.form.douyin_url" placeholder="粘贴抖音链接或分享文案" clearable>
            <template #append><el-button :loading="parsing" @click="doParse">解析</el-button></template>
          </el-input>
          <div v-if="dialog.form.share_text" class="parse-tip" :class="{ 'is-warn': !dialog.form.title_from_text }">
            <template v-if="dialog.form.title_from_text">
              已识别：{{ dialog.form.title || '未命名' }}
              <template v-if="dialog.form.tags && dialog.form.tags.length"> · {{ dialog.form.tags.map((t) => '#' + t).join(' ') }}</template>
              <template v-if="dialog.form.video_id"> · ID {{ dialog.form.video_id }}</template>
            </template>
            <template v-else>已保留原始短链，抖音未开放标题接口，请手动补充名称</template>
          </div>
          <div v-if="dialog.duplicate" class="parse-duplicate-tip">
            该视频已收集过：{{ dialog.duplicate.title }}。请勿重复提交，可直接到列表中查看。
          </div>
        </el-form-item>
        <el-form-item label="视频名称" prop="title">
          <el-input v-model="dialog.form.title" placeholder="解析后自动填充，可手动修改" />
        </el-form-item>
        <el-form-item label="封面截图" prop="cover" required>
          <div class="cover-edit">
            <ImageUploader
              :src="dialog.form.cover"
              mode="single"
              shape="square"
              :size="100"
              @update:src="(url) => (dialog.form.cover = url)"
            />
            <span class="cover-tip">解析链接时自动获取封面，也可手动上传替换</span>
          </div>
        </el-form-item>
        <el-form-item label="类别" prop="category_id" required>
          <el-select v-model="dialog.form.category_id" placeholder="请选择，在配置中心管理" style="width: 100%">
            <el-option v-for="c in categories" :key="c.id" :label="c.name" :value="c.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="作者" prop="author" required>
          <el-input v-model="dialog.form.author" placeholder="解析链接时自动获取，也可手动填写" />
        </el-form-item>
        <el-form-item label="话题标签" prop="tags">
          <TagSelect v-model="dialog.form.tags" placeholder="从话题标签库选择，或输入新话题标签回车创建" />
        </el-form-item>
        <el-form-item label="视频信息">
          <div class="video-data-edit is-meta">
            <div class="video-data-field">
              <label title="发布时间"><el-icon><Calendar /></el-icon></label>
              <el-date-picker
                v-model="dialog.form.published_at"
                type="date"
                value-format="YYYY-MM-DD"
                placeholder="选择日期"
                size="small"
                style="width: 100%"
              />
            </div>
            <div class="video-data-field">
              <label title="视频时长（秒）"><SocialIcon name="duration" :size="14" /></label>
              <el-input-number v-model="dialog.form.duration" :min="0" :max="86400" :precision="1" controls-position="right" size="small" />
            </div>
          </div>
        </el-form-item>
        <el-form-item label="视频数据" prop="like_count" required>
          <div class="video-data-edit">
            <div class="video-data-field">
              <label class="is-like" title="喜欢数"><SocialIcon name="heart" :size="14" /></label>
              <el-input-number v-model="dialog.form.like_count" :min="0" :max="99999999" :controls="false" size="small" />
            </div>
            <div class="video-data-field">
              <label title="评论数"><SocialIcon name="comment" :size="14" /></label>
              <el-input-number v-model="dialog.form.comment_count" :min="0" :max="99999999" :controls="false" size="small" />
            </div>
            <div class="video-data-field">
              <label title="收藏数"><SocialIcon name="star" :size="14" /></label>
              <el-input-number v-model="dialog.form.collect_count" :min="0" :max="99999999" :controls="false" size="small" />
            </div>
            <div class="video-data-field">
              <label title="转发数"><SocialIcon name="share" :size="14" /></label>
              <el-input-number v-model="dialog.form.share_count" :min="0" :max="99999999" :controls="false" size="small" />
            </div>
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="dialog.form.remark" type="textarea" :rows="2" placeholder="创意亮点、参考理由等" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="dialog.saving" @click="save">保存</el-button>
      </template>
    </el-dialog>

    <!-- 评论弹窗：多人可发表意见 -->
    <el-dialog v-model="comment.visible" width="560px" :close-on-click-modal="false">
      <template #header>
        <DialogHeader
          :icon="ChatLineRound"
          title="创意评论"
          :sub="`${comment.row?.title || '未命名创意'} · 多人可在此发表意见`"
          tone="blue"
        />
      </template>

      <div class="comment-body">
        <div v-if="comment.loading" class="comment-empty">加载中…</div>
        <div v-else-if="!comment.list.length" class="comment-empty">
          还没有评论，来说说你的想法吧
        </div>
        <div v-else class="comment-list">
          <div v-for="c in comment.list" :key="c.id" class="comment-item">
            <div class="comment-avatar">{{ (c.user_name || '?').slice(0, 1).toUpperCase() }}</div>
            <div class="comment-main">
              <div class="comment-head">
                <span class="comment-user">{{ c.user_name || '匿名' }}</span>
                <span class="comment-time">{{ formatDateTime(c.created_at) }}</span>
                <el-button
                  v-if="c.is_owner"
                  type="text"
                  size="small"
                  class="danger-text comment-del"
                  @click="removeComment(c)"
                >删除</el-button>
              </div>
              <div class="comment-content">{{ c.content }}</div>
            </div>
          </div>
        </div>

        <div class="comment-editor">
          <el-input
            v-model="comment.text"
            type="textarea"
            :rows="3"
            maxlength="500"
            show-word-limit
            placeholder="写下你的意见或建议…"
          />
          <div class="comment-editor-foot">
            <span class="form-tip">评论仅用于讨论，不影响创意状态与排期</span>
            <el-button type="primary" :loading="comment.saving" @click="submitComment">发表</el-button>
          </div>
        </div>
      </div>

      <template #footer>
        <el-button @click="comment.visible = false">关闭</el-button>
      </template>
    </el-dialog>

    <!-- 创作计划弹窗：设置紧急程度 / 创作人 / 制作时间，保存后进入已排期 -->
    <el-dialog v-model="plan.visible" width="520px" :close-on-click-modal="false">
      <template #header>
        <DialogHeader
          :icon="Calendar"
          title="创作计划"
          :sub="`${plan.row?.title || '未命名创意'} · 设置后进入已排期，制作时间到自动开始制作`"
          tone="blue"
        />
      </template>
      <el-form ref="planFormRef" :model="plan.form" label-width="88px" label-position="right">
        <el-form-item label="紧急程度">
          <el-select v-model="plan.form.priority" placeholder="请选择紧急程度" style="width: 100%">
            <el-option v-for="p in PLAN_PRIORITY_OPTIONS" :key="p.value" :label="p.label" :value="p.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="制作人">
          <el-select
            v-model="plan.form.creator_id"
            placeholder="请选择制作人"
            clearable
            filterable
            style="width: 100%"
          >
            <el-option v-for="u in creatorOptions" :key="u.id" :label="u.display_name" :value="u.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="制作时间">
          <el-date-picker
            v-model="plan.form.planned_at"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="请选择制作日期"
            style="width: 100%"
          />
          <div class="form-tip">默认今日；到制作日期后自动进入「制作中」并生成制作记录</div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="plan.visible = false">取消</el-button>
        <el-button type="primary" :loading="plan.saving" @click="savePlan">保存并排期</el-button>
      </template>
    </el-dialog>

    <!-- 取消排期确认 -->
    <ConfirmDialog
      v-model="cancelPlanState.visible"
      title="取消排期"
      :message="`确定取消「${cancelPlanState.row?.title || '该创意'}」的创作排期吗？状态将回退到未使用。`"
      :loading="cancelPlanState.loading"
      confirm-text="确认取消排期"
      variant="warning"
      icon="warning"
      @confirm="doCancelPlan"
    />

    <!-- 删除确认 -->
    <ConfirmDialog
      v-model="confirm.visible"
      :title="confirm.title"
      :message="confirm.message"
      :loading="confirm.loading"
      @confirm="doRemove"
    />
  </div>
</template>

<script setup>
import { computed, nextTick, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  Calendar,
  ChatLineRound,
  CircleCheckFilled,
  Collection,
  Plus,
  Search,
  Star,
  Timer
} from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import AppPagination from '../components/ui/AppPagination.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import ImageUploader from '../components/ui/ImageUploader.vue'
import OptionBadge from '../components/ui/OptionBadge.vue'
import SocialIcon from '../components/ui/SocialIcon.vue'
import StatCard from '../components/ui/StatCard.vue'
import TagCell from '../components/ui/TagCell.vue'
import TagSelect from '../components/ui/TagSelect.vue'
import {
  api,
  PLAN_PRIORITY_OPTIONS,
  formatDate,
  formatDateTime,
  ideaStatusType,
  ideaStatusLabel,
  planPriorityLabel
} from '../api'
import { useAuthStore } from '../stores/auth'
import { usePermissionStore } from '../stores/permission'
import { useSettingsStore } from '../stores/settings'

const auth = useAuthStore()
const perm = usePermissionStore()
const settings = useSettingsStore()
const route = useRoute()

const PAGE_SIZE = ref(12)
// 标签筛选：已使用 = 除「未使用」外的全部状态；备选库 = 独立备选标记
const USAGE_FILTER_OPTIONS = [
  { value: 'all', label: '全部' },
  { value: 'used', label: '已使用' },
  { value: 'unused', label: '未使用' },
  { value: 'backup', label: '备选库' }
]

const loading = ref(false)
const parsing = ref(false)
const votingId = ref(null)
const list = ref([])
const categories = ref([])
const keyword = ref('')
const usage = ref('all')
const scope = ref('all')
const page = ref(1)

function isToday(value) {
  if (!value) return false
  const d = new Date(value)
  if (Number.isNaN(d.getTime())) return false
  const now = new Date()
  return d.getFullYear() === now.getFullYear() && d.getMonth() === now.getMonth() && d.getDate() === now.getDate()
}

// 四项统计基于当前可见范围的全部创意，不受标签筛选 / 搜索影响
const counts = computed(() => {
  const all = list.value
  return {
    total: all.length,
    used: all.filter((i) => i.status !== '未使用').length,
    unused: all.filter((i) => i.status === '未使用').length,
    today: all.filter((i) => isToday(i.created_at)).length
  }
})

const statCards = computed(() => [
  { label: '创意总量', value: counts.value.total, icon: Collection, tone: 'blue' },
  { label: '已使用', value: counts.value.used, icon: CircleCheckFilled, tone: 'mint' },
  { label: '未使用', value: counts.value.unused, icon: Timer, tone: 'amber' },
  { label: '今日新增', value: counts.value.today, icon: Calendar, tone: 'lilac' }
])

// 标签 / 关键词均在前端过滤，保证统计卡始终反映全量数据
const filteredList = computed(() => {
  const kw = (keyword.value || '').trim().toLowerCase()
  return list.value.filter((i) => {
    if (usage.value === 'used' && i.status === '未使用') return false
    if (usage.value === 'unused' && i.status !== '未使用') return false
    if (usage.value === 'backup' && !i.is_backup) return false
    if (!kw) return true
    return [i.title, i.author, i.douyin_url, i.share_text, i.remark]
      .some((v) => String(v || '').toLowerCase().includes(kw))
  })
})

// 客户端分页
const pagedList = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE.value
  return filteredList.value.slice(start, start + PAGE_SIZE.value)
})

watch([keyword, usage], () => { page.value = 1 })

const dialog = reactive({ visible: false, isEdit: false, id: null, saving: false, submitted: false, form: emptyForm(), duplicate: null })
const formRef = ref(null)
// 视频名称 / 话题标签允许为空，保存时自动补默认值；视频数据四项合并成一个校验点
// 规则始终挂载以显示必填星号；trigger 设为不存在的事件，
// 避免弹窗挂载 / 失焦 / 选项变化时自动弹红字，校验只在点击保存时手动 validate()。
const NO_AUTO_TRIGGER = 'manual-save-only'
const formRules = {
  douyin_url: [{ required: true, message: '请粘贴抖音链接', trigger: NO_AUTO_TRIGGER }],
  cover: [{ required: true, message: '请上传封面截图', trigger: NO_AUTO_TRIGGER }],
  category_id: [{ required: true, message: '请选择类别', trigger: NO_AUTO_TRIGGER }],
  author: [{ required: true, message: '请填写作者', trigger: NO_AUTO_TRIGGER }],
  like_count: [{
    required: true,
    validator: (_rule, _value, callback) => {
      const nums = [
        dialog.form.like_count,
        dialog.form.comment_count,
        dialog.form.collect_count,
        dialog.form.share_count
      ]
      if (nums.some((n) => n === null || n === undefined || n === '' || Number.isNaN(Number(n)))) {
        callback(new Error('请填写完整的视频数据'))
      } else {
        callback()
      }
    },
    trigger: NO_AUTO_TRIGGER
  }]
}
const confirm = reactive({ visible: false, loading: false, title: '', message: '', id: null })
const comment = reactive({ visible: false, loading: false, saving: false, row: null, list: [], text: '' })
// 创作计划弹窗（初始态点图标排期）
const planFormRef = ref(null)
const plan = reactive({ visible: false, saving: false, row: null, form: emptyPlanForm() })
// 取消排期确认
const cancelPlanState = reactive({ visible: false, loading: false, row: null })
// 创作人候选（创作计划弹窗用）
const creatorOptions = ref([])

function emptyPlanForm() {
  // 制作时间默认今日；当前账户为「创作」角色时制作人默认填自己
  const isProductionRole = auth.user?.module_role === 'production'
  return {
    priority: 2,
    creator_id: isProductionRole ? (auth.user?.id ?? null) : null,
    planned_at: todayDate()
  }
}

function emptyForm() {
  return {
    title: '', cover: '', category_id: null, douyin_url: '', video_id: '',
    share_text: '', author: '', tags: [], remark: '', title_from_text: false,
    play_count: 0, like_count: 0, comment_count: 0, collect_count: 0, share_count: 0,
    duration: null, published_at: null,
    creator_id: null, priority: 2, planned_at: null
  }
}

// 大数字缩写：1234 → 1.2k
function formatCount(n) {
  const v = Number(n || 0)
  if (v >= 100000000) return (v / 100000000).toFixed(1).replace(/\.0$/, '') + '亿'
  if (v >= 10000) return (v / 10000).toFixed(1).replace(/\.0$/, '') + 'w'
  if (v >= 1000) return (v / 1000).toFixed(1).replace(/\.0$/, '') + 'k'
  return String(v)
}

// 今日日期（YYYY-MM-DD，本地时区），用于创作计划默认制作时间
function todayDate() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}

async function load() {
  loading.value = true
  try {
    // 只按成员范围取全量，其余条件在前端过滤，保证四项统计口径一致
    const { data } = await api.get('/ideas', { params: { scope: scope.value } })
    list.value = data
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败，请重试')
  } finally {
    loading.value = false
  }
}

// 服务端返回当前用户最新额度，同步到所有行，避免只改一行导致额度显示不一致
function syncQuota(data) {
  if (!data) return
  list.value.forEach((item) => {
    if (typeof data.vote_daily_limit === 'number') item.vote_daily_limit = data.vote_daily_limit
    if (typeof data.vote_used_today === 'number') item.vote_used_today = data.vote_used_today
    if (typeof data.vote_exhausted === 'boolean') item.vote_exhausted = data.vote_exhausted
  })
}

// 投票规则：今日已用达到上限且自己未投时，不能再投（取消投票不受限）
function isVoteExhausted(row) {
  if (row.voted) return false
  const limit = row.vote_daily_limit ?? 0
  return limit > 0 && (row.vote_used_today ?? 0) >= limit
}

function voteTitle(row) {
  if (row.voted) return '取消投票'
  if (isVoteExhausted(row)) return `今日投票次数已用完（上限 ${row.vote_daily_limit} 次）`
  return '点赞投票'
}

function voteTooltip(row) {
  const limit = row.vote_daily_limit ?? 0
  const used = row.vote_used_today ?? 0
  const rule = limit ? `今日已投 ${used}/${limit}` : '投票已关闭'
  const voters = row.votes
    ? `${row.voter_names?.join('、') || ''} 已投票${row.voted ? `（含 ${auth.displayName}）` : ''}`
    : '还没有人投票，点我支持'
  return `${voters} · ${rule}`
}

// 点赞投票：一人一票，再次点击取消；乐观更新后用服务端数据校正
async function toggleVote(row) {
  if (votingId.value === row.id) return
  votingId.value = row.id
  const before = { votes: row.votes, voted: row.voted, voter_names: row.voter_names }
  // 乐观切换
  row.voted = !row.voted
  row.votes = (row.votes || 0) + (row.voted ? 1 : -1)
  try {
    const { data } = await api.post(`/ideas/${row.id}/vote`)
    row.votes = data.votes
    row.voted = data.voted
    row.voter_names = data.voter_names
    syncQuota(data)
    ElMessage.success(data.voted ? '已点赞支持' : '已取消点赞')
  } catch (e) {
    // 失败回滚
    row.votes = before.votes
    row.voted = before.voted
    row.voter_names = before.voter_names
    ElMessage.error(e.response?.data?.detail || '投票失败，请重试')
    // 达上限时刷新列表，让所有行的额度状态保持准确
    if (e.response?.status === 400) load()
  } finally {
    votingId.value = null
  }
}

// 创意灵感仅归属人/管理员可改
function canEditStatus(row) {
  return perm.can('ideas.edit') && (row.is_owner || auth.isAdmin)
}

// 点击状态标签切换备选标记：所有状态均可点，纯标记切换，不改流程状态
async function toggleBackup(row) {
  if (!canEditStatus(row)) return
  const before = row.is_backup
  row.is_backup = !before
  try {
    const { data } = await api.put(`/ideas/${row.id}/backup`, { is_backup: row.is_backup })
    row.is_backup = data.is_backup
    ElMessage.success(data.is_backup ? '已标记为备选' : '已取消备选标记')
  } catch (e) {
    row.is_backup = before
    ElMessage.error(e.response?.data?.detail || '备选标记修改失败')
  }
}

// 打开创作计划弹窗（初始态点图标）
function openPlan(row) {
  if (!canEditStatus(row)) return
  loadCreators()
  plan.row = row
  plan.form = emptyPlanForm()
  plan.visible = true
  nextTick(() => planFormRef.value?.clearValidate())
}

// 保存创作计划：设置紧急程度 / 制作人 / 制作时间 → 状态进「已排期」，排期时间到自动进制作中
async function savePlan() {
  if (!plan.row) return
  plan.saving = true
  try {
    // 制作时间只选日期：归一到当天末尾，避免默认今日时刚排期就被到期任务立即流转到「制作中」
    const payload = {
      ...plan.form,
      planned_at: plan.form.planned_at ? `${plan.form.planned_at}T23:59:59` : null
    }
    const { data } = await api.put(`/ideas/${plan.row.id}/arrange`, payload)
    ElMessage.success(`已排期，状态更新为「${data.status}」`)
    plan.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '排期失败')
  } finally {
    plan.saving = false
  }
}

// 已排期/制作中点创作计划图标：确认是否取消排期
function openCancelPlan(row) {
  if (!canEditStatus(row)) return
  cancelPlanState.row = row
  cancelPlanState.visible = true
}

async function doCancelPlan() {
  if (!cancelPlanState.row) return
  cancelPlanState.loading = true
  try {
    const { data } = await api.post(`/ideas/${cancelPlanState.row.id}/cancel-plan`)
    ElMessage.success(`排期已取消，状态回退到「${data.status}」`)
    cancelPlanState.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '取消排期失败')
  } finally {
    cancelPlanState.loading = false
  }
}

// 加载创作人候选（编辑表单用）
async function loadCreators() {
  try {
    const { data } = await api.get('/ideas/creator-options')
    creatorOptions.value = Array.isArray(data) ? data : []
  } catch (e) {
    creatorOptions.value = []
  }
}

function openCreate() {
  dialog.isEdit = false
  dialog.id = null
  dialog.submitted = false
  dialog.duplicate = null
  dialog.form = emptyForm()
  dialog.visible = true
  loadCreators()
  nextTick(() => formRef.value?.clearValidate())
}

function openEdit(row) {
  dialog.isEdit = true
  dialog.id = row.id
  dialog.submitted = false
  dialog.duplicate = null
  dialog.form = {
    title: row.title, cover: row.cover || '', category_id: row.category_id || null,
    douyin_url: row.douyin_url, video_id: row.video_id || '',
    share_text: row.share_text, author: row.author, tags: [...(row.tags || [])],
    remark: row.remark, title_from_text: true,
    play_count: row.play_count || 0, like_count: row.like_count || 0,
    comment_count: row.comment_count || 0, collect_count: row.collect_count || 0,
    share_count: row.share_count || 0,
    duration: row.duration != null ? row.duration : null,
    published_at: row.published_at ? formatDate(row.published_at) : null,
    creator_id: row.creator_id || null, priority: row.priority || 2,
    planned_at: row.planned_at ? formatDate(row.planned_at) + 'T00:00:00' : null
  }
  dialog.visible = true
  loadCreators()
  nextTick(() => formRef.value?.clearValidate())
}

// 打开评论弹窗并拉取评论列表
async function openComments(row) {
  comment.row = row
  comment.list = []
  comment.text = ''
  comment.visible = true
  comment.loading = true
  try {
    const { data } = await api.get(`/ideas/${row.id}/comments`)
    comment.list = Array.isArray(data) ? data : []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载评论失败')
  } finally {
    comment.loading = false
  }
}

async function submitComment() {
  const text = (comment.text || '').trim()
  if (!text) return ElMessage.warning('请输入评论内容')
  if (!comment.row) return
  comment.saving = true
  try {
    const { data } = await api.post(`/ideas/${comment.row.id}/comments`, { content: text })
    comment.list.push(data)
    comment.text = ''
    comment.row.comment_total = (comment.row.comment_total || 0) + 1
    ElMessage.success('评论已发表')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '发表失败')
  } finally {
    comment.saving = false
  }
}

async function removeComment(c) {
  try {
    await api.delete(`/ideas/${comment.row.id}/comments/${c.id}`)
    comment.list = comment.list.filter((x) => x.id !== c.id)
    comment.row.comment_total = Math.max(0, (comment.row.comment_total || 0) - 1)
    ElMessage.success('评论已删除')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

async function doParse() {
  const text = (dialog.form.douyin_url || '').trim()
  if (!text) return ElMessage.warning('请先粘贴抖音链接或分享文案')
  parsing.value = true
  try {
    const { data } = await api.post('/ideas/parse', {
      text, auto_fetch: true, exclude_id: dialog.isEdit ? dialog.id : null
    })
    // 解析阶段即按视频 ID 判重，命中后在表单给出醒目提示，保存时还会再次拦截
    dialog.duplicate = data.duplicate_id
      ? { id: data.duplicate_id, title: data.duplicate_title || '未命名创意' }
      : null
    dialog.form.title = data.title || dialog.form.title
    dialog.form.douyin_url = data.url || dialog.form.douyin_url
    dialog.form.video_id = data.video_id || ''
    dialog.form.share_text = data.raw || text
    dialog.form.title_from_text = !!data.title_from_text
    if (data.tags && data.tags.length) dialog.form.tags = data.tags
    // 自动抓取回填：作者 / 封面 / 视频数据
    if (data.author) dialog.form.author = data.author
    if (data.cover) dialog.form.cover = data.cover
    if (data.like_count) dialog.form.like_count = data.like_count
    if (data.comment_count) dialog.form.comment_count = data.comment_count
    if (data.collect_count) dialog.form.collect_count = data.collect_count
    if (data.share_count) dialog.form.share_count = data.share_count
    if (data.duration != null) dialog.form.duration = data.duration
    if (data.published_at) dialog.form.published_at = formatDate(data.published_at)
    if (dialog.duplicate) {
      ElMessage.warning(`该视频已收集过「${dialog.duplicate.title}」，请勿重复提交`)
    } else if (data.fetch_status === 'auto') {
      ElMessage.success('解析成功，已自动获取作者、封面、发布时间、时长与视频数据，可手动调整')
    } else if (data.title_from_text) {
      ElMessage.success('解析成功，已生成名称并保留原始短链')
    } else {
      ElMessage.warning(data.message || '已保留原始短链，请手动补充名称')
    }
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '解析失败')
  } finally {
    parsing.value = false
  }
}

async function save() {
  // 点击保存后才挂上规则并校验；打开弹窗时的空值变化不再弹红字
  dialog.submitted = true
  await nextTick()
  try {
    await formRef.value?.validate()
  } catch (_) {
    return ElMessage.warning('请补全必填项后再保存')
  }
  // 解析阶段已判重，保存时再拦截一次（防止用户忽略提示后仍提交）
  if (dialog.duplicate) {
    return ElMessage.warning(`该视频已收集过「${dialog.duplicate.title}」，请勿重复提交`)
  }
  // 视频名称 / 话题标签可空：保存前按作者名补齐默认值
  const author = String(dialog.form.author || '').trim().replace(/^@/, '')
  if (!String(dialog.form.title || '').trim()) {
    dialog.form.title = author ? `@${author}创作内容` : '@未知作者创作内容'
  }
  const tags = Array.isArray(dialog.form.tags)
    ? dialog.form.tags.map((t) => String(t || '').trim()).filter(Boolean)
    : []
  dialog.form.tags = tags.length ? tags : ['无标签']

  dialog.saving = true
  try {
    if (dialog.isEdit) await api.put(`/ideas/${dialog.id}`, { ...dialog.form })
    else await api.post('/ideas', { ...dialog.form })
    ElMessage.success('已保存')
    dialog.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    dialog.saving = false
  }
}

function remove(row) {
  confirm.title = '删除创意'
  confirm.message = `确定删除「${row.title || '未命名创意'}」吗？删除后无法恢复。`
  confirm.id = row.id
  confirm.visible = true
}

async function doRemove() {
  confirm.loading = true
  try {
    await api.delete(`/ideas/${confirm.id}`)
    ElMessage.success('已删除')
    confirm.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    confirm.loading = false
  }
}

onMounted(async () => {
  const kw = route.query.keyword
  if (typeof kw === 'string' && kw) keyword.value = kw
  await settings.load()
  categories.value = settings.categories
  load()
})

watch(() => route.query.keyword, (kw) => {
  if (typeof kw === 'string' && kw !== keyword.value) {
    keyword.value = kw
    page.value = 1
    load()
  }
})
</script>

<style scoped>

/* 创意灵感表格封面放大（全局默认 44px，仅本页覆盖，不影响发布数据/视频创作） */
.adm-cell-cover :deep(.adm-cover-thumb) {
  width: 64px;
  height: 64px;
  border-radius: 10px;
}

/* 视频名称第二行：作者 + 类别 */
.idea-author {
  color: var(--adm-text-secondary);
  margin-right: 6px;
}
.idea-cat {
  transform: scale(0.92);
  transform-origin: left center;
}
/* 视频名称第三行：发布时间 + 时长（解析回填，小字） */
.idea-video-meta {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-top: 3px;
  font-size: 11px;
  line-height: 1.4;
  color: var(--adm-text-placeholder, #a8abb2);
}
.idea-meta-item {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  white-space: nowrap;
}
.idea-meta-sep { opacity: 0.6; }

/* 创意提供：上提交人标签、下提交时间（两者同宽、日期小字） */
.idea-owner-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 100%;
}
.idea-owner-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 106px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  background: var(--adm-blue-bg, #eef4ff);
  color: var(--el-color-primary, #4a7cc4);
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.idea-owner-date {
  display: block;
  box-sizing: border-box;
  width: 106px;
  text-align: center;
  font-size: 10.5px;
  color: var(--adm-text-placeholder, #a8abb2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 点赞评论：点赞与系统评论并排 */
.idea-feedback-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 14px;
  width: 100%;
}

/* 视频数据列：两行两列（喜欢 / 评论 / 收藏 / 转发），每项为「图标 + 数字」 */
.video-stat {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  align-items: center;
  justify-items: center;
  gap: 5px 8px;
  width: 100%;
  font-variant-numeric: tabular-nums;
}
.video-stat-item {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  min-width: 52px;
  white-space: nowrap;
}
.video-stat-ico {
  display: inline-flex;
  align-items: center;
  justify-content: center;
}
.video-stat-num {
  font-size: 12px;
  font-weight: 600;
  color: var(--adm-text-regular, #303133);
}
/* 四项各自主题色：喜欢红 / 评论蓝 / 收藏橙 / 转发青 */
.video-stat-item.is-like .video-stat-ico { color: #e8474f; }
.video-stat-item.is-comment .video-stat-ico { color: #4a7cc4; }
.video-stat-item.is-collect .video-stat-ico { color: #e6932c; }
.video-stat-item.is-share .video-stat-ico { color: #3da377; }

/* 「我想做」认领单元格：初始图标，认领后显示姓名 */
.want-cell {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-wrap: nowrap;
}
.want-btn,
.want-readonly {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 30px;
  min-height: 28px;
  padding: 0 6px;
  border: 1px solid var(--adm-border);
  border-radius: 9px;
  background: var(--adm-surface-sunken);
  color: var(--adm-text-secondary);
  font-size: 13px;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}
.want-btn:hover:not(:disabled) {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
  background: var(--adm-blue-bg);
}
.want-btn.is-marked {
  border-color: var(--el-color-primary);
  color: var(--el-color-primary);
  background: var(--adm-blue-bg);
}
.want-btn.is-taken,
.want-btn:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
.want-readonly {
  cursor: default;
}
.want-name {
  max-width: 62px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 12.5px;
}
.want-name.is-mine {
  color: var(--el-color-primary);
  font-weight: 600;
}

/* 状态标签：默认无星标，点击切换备选标记；点亮后状态前出现琥珀星标 */
.status-tag-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-height: 24px;
  padding: 2px 4px;
  border: 1px solid transparent;
  border-radius: 9px;
  background: transparent;
  cursor: pointer;
  transition: all 0.2s ease;
}
.status-tag-btn:hover:not(:disabled) {
  border-color: var(--adm-border);
  background: var(--adm-surface-sunken, #f5f7fa);
}
.status-tag-btn.is-backup:hover:not(:disabled) {
  border-color: var(--el-color-warning);
  background: var(--adm-amber-bg, #fdf6ec);
}
.status-tag-btn:disabled { cursor: default; }
.status-star-on {
  color: #e6a23c;
}
.status-star-on .el-icon {
  fill: rgba(230, 162, 60, 0.22);
}


/* 创作计划默认图标：未使用态点击排期；无背景块，仅图标着色 */
.plan-icon-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 34px;
  height: 34px;
  border: none;
  background: transparent;
  color: var(--el-color-primary, #409eff);
  cursor: pointer;
  transition: transform 0.2s ease, color 0.2s ease;
}
.plan-icon-btn:hover:not(:disabled) {
  color: var(--el-color-primary-dark-2, #337ecc);
  transform: scale(1.12);
}
.plan-icon-btn:disabled { cursor: default; opacity: 0.4; }

/* 创作计划单元格：左优先级，右上创作人标签，右下排期日期 */
.arrange-cell {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  width: 100%;
}
/* 已排期态做成按钮：制作中可点取消排期（无背景无边框，仅 hover 变色提示可点） */
.arrange-cell--btn {
  padding: 4px 6px;
  border: 0;
  border-radius: 9px;
  background: transparent;
  cursor: default;
}
.arrange-cell--btn.is-cancellable {
  cursor: pointer;
  transition: color 0.2s ease;
}
.arrange-cell--btn.is-cancellable:hover .arrange-creator-tag,
.arrange-cell--btn.is-cancellable:hover .arrange-date {
  color: var(--el-color-warning);
}
/* 待发布 / 已完成：只读，制作人 + 完成时间居中，无优先级 */
.arrange-cell--done {
  cursor: default;
}
.arrange-cell--done .arrange-info {
  align-items: center;
}
.arrange-priority {
  flex: 0 0 auto;
}
.arrange-priority-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 26px;
  height: 26px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}
.arrange-priority-tag.is-p1 { color: #d4380d; background: #fff1e8; }
.arrange-priority-tag.is-p2 { color: #d48806; background: #fffbe6; }
.arrange-priority-tag.is-p3 { color: #5c6b7a; background: #f0f2f5; }
.arrange-info {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  justify-content: center;
  gap: 3px;
  min-width: 0;
}
/* 创作人标签：格式同创意提供标签，换绿色系以区分 */
.arrange-creator-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  box-sizing: border-box;
  width: 76px;
  height: 21px;
  padding: 0 5px;
  border-radius: 6px;
  background: #eaf7f0;
  color: #3da377;
  font-size: 11.5px;
  font-weight: 600;
  line-height: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.arrange-date {
  display: block;
  width: 76px;
  text-align: center;
  font-size: 10.5px;
  color: var(--adm-text-placeholder, #a8abb2);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

/* 评论按钮：无边框，图标用主题色 */
.comment-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 44px;
  height: 28px;
  padding: 0 4px;
  border: none;
  background: transparent;
  color: var(--el-color-primary, #409eff);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s ease;
}
.comment-btn .el-icon {
  color: var(--el-color-primary, #409eff);
}
.comment-btn:hover,
.comment-btn.is-active {
  color: var(--el-color-primary-dark-2, #337ecc);
}
.comment-btn:hover .el-icon,
.comment-btn.is-active .el-icon {
  color: var(--el-color-primary-dark-2, #337ecc);
}
.comment-count { font-variant-numeric: tabular-nums; }

/* 点赞投票按钮（心形图标）：无背景无边框，仅已点赞时着色 */
.vote-btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 4px;
  min-width: 52px;
  height: 28px;
  padding: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: var(--adm-text-secondary);
  font-size: 13px;
  font-weight: 600;
  cursor: pointer;
  transition: color 0.2s ease;
}
.vote-btn:hover:not(:disabled) {
  color: #e8474f;
}
.vote-btn.is-voted {
  color: #e8474f;
}
.vote-btn:disabled { cursor: default; opacity: 0.65; }
.vote-btn.is-exhausted { opacity: 0.45; }
.vote-count { font-variant-numeric: tabular-nums; }

/* 视频数据编辑：四个数字输入 */
/* 编辑表单：创作计划（创作人 / 优先级 / 排期日期） */
.plan-fields {
  width: 100%;
}
.plan-row {
  margin-top: 8px;
}
.video-data-edit {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 8px;
  width: 100%;
}
.video-data-edit.is-meta {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}
/* 图标与输入框同行，去掉文字标签，压缩弹窗高度 */
.video-data-field {
  display: flex;
  align-items: center;
  gap: 5px;
  min-width: 0;
}
.video-data-field > label {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex: 0 0 15px;
  width: 15px;
  color: var(--adm-text-secondary);
}
.video-data-field :deep(.el-input-number),
.video-data-field :deep(.el-date-editor) {
  flex: 1;
  min-width: 0;
}
.video-data-field > label .dy-icon {
  color: var(--el-color-primary);
}
.video-data-field > label.is-play .dy-icon {
  color: var(--el-color-primary);
}
.video-data-field > label.is-like .dy-icon {
  color: #e8474f;
}
.video-data-field > label.is-like .dy-icon {
  color: #e8474f;
}
.video-data-field > label .el-icon {
  color: var(--adm-text-secondary);
}
.video-data-field :deep(.el-input-number) {
  width: 100%;
}

/* 评论弹窗 */
.comment-body {
  display: flex;
  flex-direction: column;
  gap: 14px;
  max-height: 60vh;
}
.comment-list {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding-right: 4px;
}
.comment-empty {
  text-align: center;
  font-size: 13px;
  color: var(--adm-text-placeholder);
  padding: 24px 0;
}
.comment-item {
  display: flex;
  gap: 10px;
}
.comment-avatar {
  width: 30px;
  height: 30px;
  flex-shrink: 0;
  border-radius: 999px;
  background: var(--adm-blue-bg);
  color: var(--adm-blue);
  display: grid;
  place-items: center;
  font-size: 12px;
  font-weight: 700;
}
.comment-main { flex: 1; min-width: 0; }
.comment-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.comment-user {
  font-size: 12.5px;
  font-weight: 600;
  color: var(--adm-text-primary);
}
.comment-time {
  font-size: 11.5px;
  color: var(--adm-text-placeholder);
}
.comment-del {
  margin-left: auto;
  font-size: 12px;
}
.comment-content {
  margin-top: 3px;
  font-size: 13px;
  line-height: 1.6;
  color: var(--adm-text-regular);
  white-space: pre-wrap;
  word-break: break-word;
}
.comment-editor {
  border-top: 1px dashed var(--adm-border);
  padding-top: 12px;
}
.comment-editor-foot {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 8px;
  gap: 12px;
}

.parse-tip { margin-top: 6px; font-size: 12px; line-height: 1.5; color: var(--adm-text-secondary); padding: 6px 10px; border-radius: 10px; background: rgba(64, 158, 255, 0.08); }
.parse-tip.is-warn { color: var(--adm-state-warning-fg); background: var(--adm-state-warning-bg); }
.parse-duplicate-tip { margin-top: 6px; font-size: 12px; line-height: 1.5; color: #c45656; padding: 6px 10px; border-radius: 10px; background: rgba(245, 108, 108, 0.12); border: 1px solid rgba(245, 108, 108, 0.3); }

.cover-edit { display: flex; align-items: center; gap: 12px; }
.cover-tip { font-size: 12px; color: var(--adm-text-placeholder); line-height: 1.5; }
</style>
