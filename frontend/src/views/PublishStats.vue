<template>
  <div class="stack">
    <PageHeader
      :icon="TrendCharts"
      title="发布数据"
      tone="coral"
      desc="发布与数据 · 选择平台账号发布视频，记录播放、点赞、评论与转发，按时间留痕可追踪增长"
    >
      <template #extra>
        <el-select v-model="scope" style="width: 120px" @change="load">
          <el-option value="all" label="全部成员" />
          <el-option value="mine" label="仅我的" />
        </el-select>
        <el-select v-model="dataStatus" style="width: 120px" @change="onStatusChange">
          <el-option value="" label="全部状态" />
          <el-option v-for="s in DATA_STATUS_OPTIONS" :key="s.value" :value="s.value" :label="s.label" />
        </el-select>
        <el-button type="primary" :icon="VideoPlay" @click="openAutoFetch">获取抖音数据</el-button>
      </template>
    </PageHeader>

    <!-- 账号细分标签栏 -->
    <el-card shadow="never" class="adm-card account-tabs-card">
      <div class="adm-tab-bar">
        <button
          v-for="tab in accountTabs"
          :key="tab.key"
          type="button"
          class="adm-tab-chip"
          :class="{ 'is-active': selectedAccount === tab.key }"
          @click="selectAccount(tab.key)"
        >
          <img v-if="tab.avatar" :src="tab.avatar" class="adm-tab-avatar" alt="" />
          <span v-else class="adm-tab-avatar is-empty"><el-icon :size="12"><UserFilled /></el-icon></span>
          <span class="adm-tab-label">{{ tab.name }}</span>
        </button>
      </div>
      <div class="adm-tab-bar adm-status-bar">
        <span class="adm-page-desc">记录状态</span>
        <button
          v-for="tab in statusTabs"
          :key="tab.value"
          type="button"
          class="adm-tab-chip adm-tab-chip--sm"
          :class="{ 'is-active': dataStatus === tab.value }"
          @click="selectStatus(tab.value)"
        >
          <span class="adm-tab-label">{{ tab.label }}</span>
          <span class="adm-tab-count">{{ tab.count }}</span>
        </button>
        <span v-if="unrecordedCount > 0" class="unrecorded-tip">另有 {{ unrecordedCount }} 条未录入</span>
      </div>
    </el-card>

    <!-- 汇总 KPI -->
    <div class="stat-row">
      <StatCard label="累计播放" :value="total.plays || 0" :icon="VideoPlay" tone="blue" :sub-label="`${selectedAccountLabel} · ${summary.count || 0} 条`" />
      <StatCard label="累计点赞" :value="total.likes || 0" :icon="Star" tone="coral" :sub-label="`${selectedAccountLabel} · 点赞`" />
      <StatCard label="累计评论" :value="total.comments || 0" :icon="ChatDotRound" tone="lilac" :sub-label="`${selectedAccountLabel} · 评论`" />
      <StatCard label="累计转发" :value="total.shares || 0" :icon="Share" tone="mint" :sub-label="`${selectedAccountLabel} · 转发`" />
      <StatCard label="粉丝数量" :value="total.followers || 0" :icon="UserFilled" tone="amber" :sub-label="`${selectedAccountLabel} · 粉丝`" />
    </div>

    <el-card shadow="never" class="adm-card adm-card--table" :class="{ 'is-loading': loading }">
      <GridSkeleton v-if="loading" :rows="8" :cols="6" />
      <template #header>
        <div class="table-head">
          <span class="adm-section-title">已发布视频</span>
          <el-button size="small" :icon="EditPen" @click="openManualImport">手动导入</el-button>
        </div>
      </template>

      <div class="adm-table-wrap">
        <el-table :data="pagedItems" stripe style="width: 100%" empty-text="还没有已发布的视频">
          <el-table-column label="视频名称" min-width="190" align="left">
            <template #default="{ row }">
              <div class="pub-name-cell">
                <img v-if="row.cover" :src="row.cover" class="pub-cover" alt="封面" />
                <span v-else class="pub-cover is-empty">无封面</span>
                <div class="pub-name-main">
                  <a
                    v-if="videoHref(row)"
                    :href="videoHref(row)"
                    target="_blank"
                    rel="noopener"
                    class="adm-cell-text adm-cell-text--clamp2 pub-title-link"
                    :title="`${row.title || '未命名'} · 点击跳转抖音播放`"
                  >{{ row.title || '未命名' }}</a>
                  <span v-else class="adm-cell-text adm-cell-text--clamp2" :title="row.title || '未命名'">
                    {{ row.title || '未命名' }}
                  </span>
                  <!-- 第二行：绑定的创意灵感视频名称；未绑定显示「未配置」，点击可匹配 -->
                  <span
                    v-if="row.import_id"
                    class="pub-ref-name"
                    :class="{ 'is-unset': !row.reference_title, 'is-clickable': !!row.reference_title }"
                    :title="row.reference_title ? `创意视频名称：${row.reference_title} · 点击重新匹配` : '点击匹配视频创作中待发布的记录'"
                    @click="openMatchDialog(row)"
                  >{{ row.reference_title || '未配置' }}</span>
                  <span v-else class="pub-ref-name is-unset-static">{{ row.reference_title || '未配置' }}</span>
                  <!-- 第三行：@创作者 + 分类；未绑定显示「未配置」 -->
                  <div class="pub-ref-meta">
                    <template v-if="row.reference_title">
                      <span class="pub-ref-author" :title="row.owner_name || '未配置'">@{{ row.owner_name || '未配置' }}</span>
                      <OptionBadge
                        v-if="row.category_name"
                        :name="row.category_name"
                        :color="settings.option('category', row.category_name).color"
                        :image="settings.option('category', row.category_name).image"
                        :display="settings.option('category', row.category_name).display"
                        class="pub-ref-cat"
                      />
                    </template>
                    <span v-else class="pub-ref-meta-unset">未配置</span>
                  </div>
                </div>
              </div>
            </template>
          </el-table-column>

          <!-- 话题标签：与创意灵感同规则——最多三行，溢出 +N，悬浮展示剩余 -->
          <el-table-column label="话题标签" min-width="136" align="left">
            <template #default="{ row }">
              <TagCell :tags="row.tags || []" :max-lines="3" />
            </template>
          </el-table-column>

          <el-table-column label="视频数据" min-width="162" align="center">
            <template #default="{ row }">
              <div class="video-stat">
                <span class="video-stat-item is-duration" :title="row.duration != null ? '视频时长：' + Number(row.duration).toFixed(1) + 'S' : '未获取时长'">
                  <span class="video-stat-ico"><SocialIcon name="duration" :size="11" /></span>
                  <span class="video-stat-num">{{ row.duration != null ? Number(row.duration).toFixed(1) + 'S' : '—' }}</span>
                </span>
                <span class="video-stat-item is-play" title="播放量">
                  <span class="video-stat-ico"><SocialIcon name="play" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.plays) }}</span>
                </span>
                <span class="video-stat-item is-like" title="点赞量">
                  <span class="video-stat-ico"><SocialIcon name="heart" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.likes) }}</span>
                </span>
                <span class="video-stat-item is-comment" title="评论量">
                  <span class="video-stat-ico"><SocialIcon name="comment" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.comments) }}</span>
                </span>
                <span class="video-stat-item is-collect" title="收藏量">
                  <span class="video-stat-ico"><SocialIcon name="star" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.collects) }}</span>
                </span>
                <span class="video-stat-item is-share" title="转发量">
                  <span class="video-stat-ico"><SocialIcon name="share" :size="11" /></span>
                  <span class="video-stat-num">{{ formatCount(row.shares) }}</span>
                </span>
              </div>
            </template>
          </el-table-column>

          <!-- 发布状态：第一行状态标签（绿点正常/红点隐藏），第二行发布时间；两行同宽 -->
          <el-table-column label="发布状态" min-width="136" align="center">
            <template #default="{ row }">
              <div class="pub-owner-cell">
                <span class="pub-status-tag" :class="row.data_status === '隐藏' ? 'is-hidden' : 'is-normal'">
                  <i class="pub-status-dot" />{{ row.data_status === '隐藏' ? '隐藏' : '正常' }}
                </span>
                <span class="pub-owner-date adm-cell-time" :title="formatDateTime(row.published_at)">{{ formatDateTime(row.published_at) }}</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="操作" min-width="116" fixed="right" align="center">
            <template #default="{ row }">
              <div class="adm-cell-actions">
                <el-button v-if="perm.can('publish-stats.edit')" type="text" size="small" @click="openRecord(row)">更新</el-button>
                <el-button v-if="perm.can('publish-stats.delete')" type="text" size="small" class="danger-text" @click="remove(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :image-size="100" description="还没有已发布的视频" />
          </template>
        </el-table>
      </div>

      <AppPagination v-model:page="page" :total="items.length" v-model:page-size="PAGE_SIZE" />
    </el-card>

    <!-- 手动导入：隐藏 / 仅自己可见作品无法自动采集，手工录入 -->
    <el-dialog v-model="manual.visible" width="560px" class="adm-dialog-detail manual-dialog" :close-on-click-modal="false">
      <template #header>
        <DialogHeader
          :icon="EditPen"
          title="手动导入视频"
          sub="隐藏 / 仅自己可见作品不在公开列表，在此手工录入后直接写入数据表格"
          tone="coral"
        />
      </template>
      <div class="manual-body">
        <el-form label-width="88px" label-position="right">
          <el-form-item label="视频名称">
            <el-input v-model="manual.form.title" placeholder="抖音作品标题" maxlength="200" />
          </el-form-item>
          <el-form-item label="封面截图">
            <ImageUploader
              :src="manual.form.cover"
              mode="single"
              shape="square"
              :size="72"
              tip="上传作品封面截图"
              @update:src="(v) => (manual.form.cover = v)"
            />
          </el-form-item>
          <el-form-item label="话题标签">
            <el-input v-model="manual.tagsText" placeholder="多个标签用逗号分隔，如：穿搭,日常" />
          </el-form-item>
          <el-form-item label="视频数据">
            <div class="manual-metrics">
              <label>播放<el-input-number v-model="manual.form.plays" :min="0" :controls="false" /></label>
              <label>点赞<el-input-number v-model="manual.form.likes" :min="0" :controls="false" /></label>
              <label>评论<el-input-number v-model="manual.form.comments" :min="0" :controls="false" /></label>
              <label>收藏<el-input-number v-model="manual.form.collects" :min="0" :controls="false" /></label>
              <label>转发<el-input-number v-model="manual.form.shares" :min="0" :controls="false" /></label>
            </div>
          </el-form-item>
          <el-form-item label="状态">
            <el-select v-model="manual.form.data_status" style="width: 100%">
              <el-option v-for="s in DATA_STATUS_OPTIONS" :key="s.value" :value="s.value" :label="s.label" />
            </el-select>
          </el-form-item>
          <el-form-item label="发布时间">
            <el-date-picker
              v-model="manual.publishDate"
              type="datetime"
              placeholder="选择发布时间"
              style="width: 100%"
              value-format="x"
            />
          </el-form-item>
        </el-form>
      </div>
      <template #footer>
        <el-button @click="manual.visible = false">取消</el-button>
        <el-button type="primary" :loading="manual.saving" @click="saveManualImport">导入</el-button>
      </template>
    </el-dialog>

    <!-- 录入 / 编辑弹窗 -->
    <el-dialog
      v-model="record.visible"
      width="480px"
      :close-on-click-modal="false"
    >
      <template #header>
        <DialogHeader
          :icon="TrendCharts"
          :title="record.row?.stat_id ? '更新数据快照' : '录入发布数据'"
          sub="保存一条数据快照，按时间留痕可追踪增长"
          tone="coral"
        />
      </template>
      <div class="rec-title">{{ record.row?.title }}</div>
      <el-form label-width="76px" label-position="right">
        <el-form-item label="播放量">
          <el-input-number v-model="record.form.plays" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="点赞量">
          <el-input-number v-model="record.form.likes" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="评论量">
          <el-input-number v-model="record.form.comments" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="收藏量">
          <el-input-number v-model="record.form.collects" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="转发量">
          <el-input-number v-model="record.form.shares" :min="0" style="width: 100%" />
        </el-form-item>
        <el-form-item label="状态">
          <el-select v-model="record.form.data_status" style="width: 100%">
            <el-option v-for="s in DATA_STATUS_OPTIONS" :key="s.value" :value="s.value" :label="s.label" />
          </el-select>
        </el-form-item>
        <el-form-item label="发布账号">
          <el-select v-model="record.form.account" placeholder="选填，在「发布账号」模块维护" clearable filterable allow-create style="width: 100%">
            <el-option
              v-for="a in publishAccounts"
              :key="a.id"
              :label="accountLabel(a)"
              :value="a.name"
            >
              <div class="account-option">
                <img v-if="a.avatar" :src="a.avatar" alt="" class="account-option-avatar" />
                <span class="account-option-name">{{ a.name }}</span>
                <span v-if="a.platform || a.account_id" class="account-option-meta">
                  {{ [a.platform, a.account_id].filter(Boolean).join(' · ') }}
                </span>
              </div>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="采集时间">
          <el-date-picker
            v-model="record.form.recorded_at"
            type="datetime"
            placeholder="默认当前时间"
            style="width: 100%"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="record.visible = false">取消</el-button>
        <el-button type="primary" :loading="record.saving" @click="saveRecord">保存快照</el-button>
      </template>
    </el-dialog>

    <!-- 历史快照弹窗：详情弹窗样式 -->
    <el-dialog v-model="history.visible" width="720px" class="adm-dialog-detail">
      <template #header>
        <DialogHeader :icon="Clock" title="数据快照历史" sub="按采集时间倒序展示该视频的全部数据快照" tone="lilac" />
      </template>
      <div class="detail-table-wrap">
        <el-table :data="history.list" stripe size="small" empty-text="还没有历史快照">
          <el-table-column label="采集时间" width="152" align="right">
            <template #default="{ row }">
              <span class="adm-cell-time" :title="formatDateTime(row.recorded_at)">{{ formatDateTime(row.recorded_at) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="播放" prop="plays" width="88" align="right">
            <template #default="{ row }"><span class="adm-cell-num">{{ row.plays }}</span></template>
          </el-table-column>
          <el-table-column label="点赞" prop="likes" width="88" align="right">
            <template #default="{ row }"><span class="adm-cell-num">{{ row.likes }}</span></template>
          </el-table-column>
          <el-table-column label="评论" prop="comments" width="88" align="right">
            <template #default="{ row }"><span class="adm-cell-num">{{ row.comments }}</span></template>
          </el-table-column>
          <el-table-column label="转发" prop="shares" width="88" align="right">
            <template #default="{ row }"><span class="adm-cell-num">{{ row.shares }}</span></template>
          </el-table-column>
          <el-table-column label="账号" prop="account" min-width="120" show-overflow-tooltip>
            <template #default="{ row }"><span class="adm-cell-time">{{ row.account || '—' }}</span></template>
          </el-table-column>
          <template #empty>
            <el-empty :image-size="80" description="还没有历史快照" />
          </template>
        </el-table>
      </div>
    </el-dialog>
<!-- 视频预览 -->
  <el-dialog v-model="preview.visible" width="720px" title="视频预览" align-center>
    <video v-if="preview.row?.video_file" class="preview-player" :src="preview.row.video_file" controls autoplay preload="metadata" />
  </el-dialog>

  <!-- 自动采集：按抖音号 / 主页链接抓取作品播放数据 -->
  <el-dialog
    v-model="auto.visible"
    width="760px"
    class="adm-dialog-detail"
    :close-on-click-modal="false"
    destroy-on-close
  >
    <template #header>
      <DialogHeader
        :icon="VideoPlay"
        title="获取抖音视频列表"
        sub="按账号与条数拉取公开作品列表与播放数据，导入后直接写入发布数据表格"
        tone="coral"
      />
    </template>
    <div class="auto-body">
      <div class="auto-query">
        <el-select
          v-model="auto.account_id"
          placeholder="选择账号"
          style="width: 180px"
          @change="clearAutoResult"
        >
          <el-option
            v-for="a in douyinAccounts"
            :key="a.id"
            :label="a.name"
            :value="a.id"
          />
        </el-select>
        <el-select v-model="auto.limit" style="width: 128px">
          <el-option value="all" label="全部" />
          <el-option :value="1" label="最近 1 条" />
          <el-option :value="5" label="最近 5 条" />
          <el-option :value="10" label="最近 10 条" />
          <el-option :value="20" label="最近 20 条" />
        </el-select>
        <el-button type="primary" :loading="auto.loading" @click="fetchDouyinList">
          获取视频列表
        </el-button>
        <el-button
          type="success"
          plain
          :loading="auto.batchImporting"
          :disabled="!selectedAutoVideos.length"
          @click="importVideos(selectedAutoVideos)"
        >
          批量导入（{{ selectedAutoVideos.length }}）
        </el-button>
      </div>
      <div class="auto-config">
        <el-checkbox v-model="autoCheckImported">
          已导入作品自动勾选（仅勾选的才写入/更新，取消勾选则不更新）
        </el-checkbox>
        <span v-if="pageBuildTime" class="auto-build-time">页面版本 {{ pageBuildTime }}</span>
      </div>
      <div class="auto-tip">
        账号默认跟随当前账号标签，条数默认「全部」。仅能采集主页公开展示的作品；采集完整时会自动对账：已录入但不在公开列表的作品标记为「隐藏」，重新公开的自动恢复「正常」，隐藏作品不计入顶部统计。
      </div>
      <div v-if="auto.message" class="auto-error">
        {{ auto.message }}
        <div v-if="auto.need_login" class="auto-error-hint">
          请先到「我的账号」页完成该账号扫码登录，再回来重试。
        </div>
      </div>
      <div v-if="auto.videos.length" class="auto-list-head">
        <label class="auto-check-all">
          <el-checkbox v-model="auto.allChecked" @change="toggleAllAuto" />
          <span>共 {{ auto.videos.length }} 条作品 · {{ auto.accountLabel || '当前账号' }}</span>
        </label>
        <span class="auto-list-hint">勾选后批量导入，也可单条导入；导入后直接出现在下方表格</span>
      </div>
      <div v-if="auto.videos.length" class="auto-list">
        <div v-for="(v, i) in auto.videos" :key="v.video_id || i" class="auto-row">
          <el-checkbox v-model="auto.checked[i]" class="auto-row-check" @change="syncAutoAllChecked" />
          <img v-if="v.cover" :src="v.cover" class="auto-cover" :alt="v.title" />
          <img v-else src="/placeholder.svg" class="auto-cover is-empty" alt="暂无封面" />
          <div class="auto-info">
            <div class="auto-title">
              {{ v.title || '未命名作品' }}
              <span v-if="v.imported" class="auto-imported-badge">已导入</span>
              <span v-if="v.account_name" class="auto-video-account">{{ v.account_name }}</span>
            </div>
            <div class="auto-nums">
              播放 {{ formatCount(v.plays) }} · 点赞 {{ formatCount(v.likes) }} · 评论 {{ formatCount(v.comments) }} · 收藏 {{ formatCount(v.collects) }} · 转发 {{ formatCount(v.shares) }}
              <span v-if="v.duration"> · 时长 {{ Number(v.duration).toFixed(1) }}S</span>
              <span v-if="v.create_time"> · {{ formatDateTime(v.create_time * 1000) }}</span>
            </div>
            <div class="auto-tags">
              <TagCell :tags="v.tags || []" />
            </div>
          </div>
          <el-tooltip :disabled="auto.checked[i]" content="请先勾选该作品；取消勾选不会更新已有数据" placement="top">
            <span>
              <el-button
                size="small"
                type="primary"
                plain
                :disabled="!auto.checked[i]"
                :loading="auto.importingId === v.video_id"
                @click="importOneVideo(v)"
              >导入</el-button>
            </span>
          </el-tooltip>
        </div>
      </div>
      <div v-else-if="!auto.message" class="auto-empty">选择账号与条数后点击「获取视频列表」，公开作品会显示在这里</div>
    </div>
    <template #footer>
      <el-button @click="auto.visible = false">关闭</el-button>
    </template>
  </el-dialog>

  <!-- 点击表格「未配置」：选择视频创作中待发布的记录作为参考视频 -->
  <el-dialog v-model="matchDialog.visible" width="640px" class="adm-dialog-detail match-dialog" :close-on-click-modal="false">
    <template #header>
      <DialogHeader
        :icon="Connection"
        title="匹配参考视频创作记录"
        sub="绿色标记为当前已关联的记录；其余仅展示未关联且状态为「待发布」的创作记录"
        tone="coral"
      />
    </template>
    <div class="match-body">
      <div class="match-source">
        <img v-if="matchDialog.row?.cover" :src="matchDialog.row.cover" class="batch-cover" alt="" />
        <span v-else class="batch-cover is-empty">—</span>
        <div class="batch-video-info">
          <div class="batch-title">{{ matchDialog.row?.title || '未命名作品' }}</div>
          <div class="auto-nums">播放 {{ formatCount(matchDialog.row?.plays) }} · 点赞 {{ formatCount(matchDialog.row?.likes) }}</div>
        </div>
      </div>
      <el-input v-model="matchDialog.keyword" placeholder="搜索创作记录名称" clearable class="match-search" />
      <div class="match-options" v-loading="matchDialog.loading">
        <!-- 当前已关联的记录：即使状态为已完成也单独置顶标记，便于识别 -->
        <div
          v-if="matchDialog.currentId"
          class="match-option is-current"
          :class="{ 'is-active': matchDialog.productionId === matchDialog.currentId }"
          @click="matchDialog.productionId = matchDialog.currentId"
        >
          <img v-if="matchDialog.currentCover" :src="matchDialog.currentCover" class="match-option-cover" alt="" />
          <span v-else class="match-option-cover is-empty">—</span>
          <div class="match-option-info">
            <div class="batch-title">
              {{ matchDialog.currentTitle || '当前关联创作记录' }}
              <span class="match-current-badge">当前关联</span>
            </div>
            <div class="auto-nums match-option-tags">
              <el-tag size="small" effect="plain" class="match-owner-tag">{{ matchDialog.currentOwner || '未归属' }}</el-tag>
            </div>
          </div>
          <el-icon v-if="matchDialog.productionId === matchDialog.currentId" class="match-check"><Check /></el-icon>
        </div>
        <div
          v-for="p in filteredMatchOptions"
          :key="p.id"
          class="match-option"
          :class="{ 'is-active': matchDialog.productionId === p.id }"
          @click="matchDialog.productionId = p.id"
        >
          <img v-if="p.cover" :src="p.cover" class="match-option-cover" alt="" />
          <span v-else class="match-option-cover is-empty">—</span>
          <div class="match-option-info">
            <div class="batch-title">{{ p.title || '未命名视频' }}</div>
            <div class="auto-nums match-option-tags">
              <span class="match-option-author">@{{ p.author || '未获取作者' }}</span>
              <el-tag size="small" effect="plain" class="match-owner-tag">{{ p.owner_name || '未归属' }}</el-tag>
              <OptionBadge
                v-if="p.category_name"
                :name="p.category_name"
                :color="settings.option('category', p.category_name).color"
                :image="settings.option('category', p.category_name).image"
                :display="settings.option('category', p.category_name).display"
                class="match-category-badge"
              />
            </div>
          </div>
          <el-icon v-if="matchDialog.productionId === p.id" class="match-check"><Check /></el-icon>
        </div>
        <div v-if="!matchDialog.currentId && !filteredMatchOptions.length && !matchDialog.loading" class="auto-empty">没有匹配的创作记录，可先到「视频创作」新建</div>
      </div>
    </div>
    <template #footer>
      <el-button @click="matchDialog.visible = false">取消</el-button>
      <el-button
        v-if="matchDialog.currentId"
        :loading="matchDialog.unmatching"
        @click="unmatchImport"
      >取消关联</el-button>
      <el-button type="primary" :loading="matchDialog.saving" :disabled="!matchDialog.productionId" @click="confirmMatch">确认关联</el-button>
    </template>
  </el-dialog>

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
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ChatDotRound, Check, Clock, Connection, EditPen, Share, Star, TrendCharts, UserFilled, VideoPlay } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import AppPagination from '../components/ui/AppPagination.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import ImageUploader from '../components/ui/ImageUploader.vue'
import OptionBadge from '../components/ui/OptionBadge.vue'
import SocialIcon from '../components/ui/SocialIcon.vue'
import StatCard from '../components/ui/StatCard.vue'
import TagCell from '../components/ui/TagCell.vue'
import { api, DATA_STATUS_OPTIONS, formatDateTime, productionStatusLabel } from '../api'
import { usePermissionStore } from '../stores/permission'
import { useSettingsStore } from '../stores/settings'

const route = useRoute()
const perm = usePermissionStore()
const settings = useSettingsStore()
const publishAccounts = ref([])

const PAGE_SIZE = ref(12)

const loading = ref(false)
const items = ref([])
const total = ref({})
// 后端返回的统计口径条数：只算正常视频，切换「隐藏」筛选时保持不变
const summaryCount = ref(0)
const accounts = ref([])
const selectedAccount = ref('')
const dataStatus = ref('')
const statusCounts = ref({ 正常: 0, 隐藏: 0 })
const unrecordedCount = ref(0)
const page = ref(1)

// 各单号单独管理：不再提供「全部账号」聚合标签；头像取自账号资料
const accountTabs = computed(() => accounts.value.map((a) => ({ key: a.key, name: a.name, avatar: a.avatar || '' })))
const selectedAccountLabel = computed(() => {
  const tab = accountTabs.value.find((t) => t.key === selectedAccount.value)
  return tab ? tab.name : '当前账号'
})

const statusTabs = computed(() => [
  {
    value: '',
    label: '全部',
    count: statusCounts.value['全部'] || (statusCounts.value['正常'] || 0) + (statusCounts.value['隐藏'] || 0)
  },
  ...DATA_STATUS_OPTIONS.map((s) => ({ ...s, count: statusCounts.value[s.value] || 0 }))
])

const record = reactive({
  visible: false,
  saving: false,
  row: null,
  form: { plays: 0, likes: 0, comments: 0, collects: 0, shares: 0, account: '', video_id: '', recorded_at: null, data_status: '正常' }
})

const confirm = reactive({ visible: false, loading: false, title: '', message: '', id: null, importId: null })
const history = reactive({ visible: false, list: [] })
const preview = reactive({ visible: false, row: null })
const auto = reactive({
  visible: false,
  loading: false,
  account_id: null,
  accountLabel: '',
  limit: 'all',
  videos: [],
  checked: [],
  allChecked: false,
  message: '',
  need_login: false,
  importingId: null,
  batchImporting: false
})

// 表格内「未配置」点击后的匹配弹窗
const matchDialog = reactive({
  visible: false, importId: null, row: null, productionId: null,
  currentId: null, currentTitle: '', currentCover: '', currentStatus: '', currentOwner: '',
  loading: false, saving: false, unmatching: false, keyword: '', options: []
})

// 手动导入：隐藏 / 仅自己可见作品
const manual = reactive({
  visible: false,
  saving: false,
  tagsText: '',
  publishDate: null,
  form: { title: '', cover: '', tags: [], plays: 0, likes: 0, comments: 0, collects: 0, shares: 0, data_status: '正常' }
})

// 已勾选的采集作品
const selectedAutoVideos = computed(() => auto.videos.filter((_, i) => auto.checked[i]))

// 页面构建时间：用于确认浏览器加载的是不是最新前端（旧缓存看不到自动勾选配置行）
const pageBuildTime = typeof __APP_BUILD_TIME__ === 'string'
  ? __APP_BUILD_TIME__.replace('T', ' ').slice(0, 16)
  : ''

// 已导入作品自动勾选：配置保存在「系统设置 → 抖音解析」，默认开启
const autoCheckImported = computed({
  get: () => settings.douyin?.auto_check_imported !== false,
  set: (value) => {
    const next = { ...(settings.items.douyin || {}), auto_check_imported: !!value }
    settings.items.douyin = next
    settings.save('douyin', next).catch(() => {
      ElMessage.warning('配置保存失败，本次仍按当前选择执行')
    })
  }
})

// 匹配弹窗：只展示待发布的创作记录，再按关键字过滤
const filteredMatchOptions = computed(() => {
  const kw = (matchDialog.keyword || '').trim().toLowerCase()
  return matchDialog.options.filter((p) => {
    if (p.status !== '待发布') return false
    if (p.id === matchDialog.currentId) return false
    return !kw || (p.title || '').toLowerCase().includes(kw)
  })
})

// 抖音账号：优先展示已扫码登录的，便于一键拉取作品列表
const douyinAccounts = computed(() => {
  const rows = publishAccounts.value.filter((a) => {
    const platform = `${a.platform || ''}`
    const home = `${a.home_url || ''}`
    return platform.includes('抖音') || home.includes('douyin.com') || a.douyin_uid || a.sec_uid
  })
  return rows.sort((a, b) => {
    const rank = (x) => (x.douyin_login_status === '已登录' ? 0 : 1)
    return rank(a) - rank(b)
  })
})

const summary = computed(() => ({ count: summaryCount.value }))

// 客户端分页
const pagedItems = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE.value
  return items.value.slice(start, start + PAGE_SIZE.value)
})

function accountLabel(a) {
  const extra = [a.platform, a.account_id].filter(Boolean).join(' · ')
  return extra ? `${a.name}（${extra}）` : a.name
}

async function load(isRetry = false) {
  loading.value = true
  try {
    const { data } = await api.get('/publish-stats/summary', {
      params: { scope: scope.value, account_key: selectedAccount.value, data_status: dataStatus.value }
    })
    accounts.value = data.accounts || []
    statusCounts.value = data.status_counts || statusCounts.value
    unrecordedCount.value = Number(data.unrecorded_count || 0)
    summaryCount.value = Number(data.count || 0)
    // 各单号单独管理：必须选中一个账号；未选中或已失效则回落到第一个账号（最多重试一次）
    if (!accounts.value.some((a) => a.key === selectedAccount.value)) {
      const next = accounts.value[0]?.key || ''
      if (next && !isRetry) {
        selectedAccount.value = next
        page.value = 1
        await load(true)
        return
      }
      // 未添加任何账号时，不展示全部账号的汇总数据
      items.value = []
      total.value = {}
      summaryCount.value = 0
      unrecordedCount.value = 0
      return
    }
    items.value = data.items || []
    total.value = data.total || {}
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败，请重试')
  } finally {
    loading.value = false
  }
}

function selectAccount(key) {
  if (selectedAccount.value === key) return
  selectedAccount.value = key
  page.value = 1
  load()
}

function selectStatus(value) {
  if (dataStatus.value === value) return
  dataStatus.value = value
  page.value = 1
  load()
}

function onStatusChange() {
  page.value = 1
  load()
}

const scope = ref('all')

function openRecord(row) {
  record.row = row
  record.form = {
    plays: row.plays || 0,
    likes: row.likes || 0,
    comments: row.comments || 0,
    collects: row.collects || 0,
    shares: row.shares || 0,
    account: row.account || '',
    video_id: row.video_id || '',
    recorded_at: null,
    data_status: row.data_status || '正常'
  }
  record.visible = true
}

async function saveRecord() {
  record.saving = true
  try {
    const { data_status: status, ...statFields } = record.form
    const isImport = !!record.row?.import_id
    if (isImport && record.row.stat_id) {
      // 采集行已关联创作记录：改快照，后端同步回采集行
      await api.put(`/publish-stats/${record.row.stat_id}`, statFields)
    } else if (isImport) {
      // 采集行尚未配置：直接改这行数据
      await api.put(`/publish-stats/imports/${record.row.import_id}`, {
        plays: statFields.plays,
        likes: statFields.likes,
        comments: statFields.comments,
        collects: statFields.collects,
        shares: statFields.shares,
        account_name: statFields.account || ''
      })
    } else if (record.row?.stat_id) {
      // 编辑已有快照
      await api.put(`/publish-stats/${record.row.stat_id}`, statFields)
    } else {
      // 新增快照
      await api.post('/publish-stats', {
        production_id: record.row.production_id,
        ...statFields
      })
    }
    // 状态单独走记录状态接口（软状态，不影响视频本身）
    if (status !== record.row.data_status) {
      if (isImport && !record.row.production_id) {
        await api.put(`/publish-stats/imports/${record.row.import_id}/status`, { status })
      } else if (record.row?.production_id) {
        await api.put(`/publish-stats/status/${record.row.production_id}`, { status })
      }
    }
    ElMessage.success(record.row?.stat_id ? '快照已更新' : '快照已保存')
    record.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    record.saving = false
  }
}

function remove(row) {
  confirm.title = '删除数据记录'
  confirm.message = `确定删除「${row.title || '未命名视频'}」的数据记录吗？删除后无法恢复。`
  confirm.id = row.stat_id
  confirm.importId = row.import_id || null
  confirm.visible = true
}

async function doRemove() {
  confirm.loading = true
  try {
    if (confirm.importId && !confirm.id) {
      await api.delete(`/publish-stats/imports/${confirm.importId}`)
    } else {
      await api.delete(`/publish-stats/${confirm.id}`)
    }
    ElMessage.success('已删除')
    confirm.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  } finally {
    confirm.loading = false
  }
}

async function openHistory(row) {
  try {
    const { data } = await api.get('/publish-stats', { params: { production_id: row.production_id } })
    history.list = data || []
    history.visible = true
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载历史失败')
  }
}

function openPreview(row) {
  preview.row = row
  preview.visible = true
}

// -------------------------------------------------- 抖音自动采集
function formatCount(n) {
  const v = Number(n || 0)
  if (v >= 100000000) return (v / 100000000).toFixed(1).replace(/\.0$/, '') + ' 亿'
  if (v >= 10000) return (v / 10000).toFixed(1).replace(/\.0$/, '') + ' 万'
  return String(v)
}

// 点击视频名称跳转到抖音播放；优先用回链，采集作品按作品 ID 拼官方播放地址
function videoHref(row) {
  if (row?.published_url) return row.published_url
  // 手动导入的虚拟 video_id 不是真实抖音作品，不生成播放链接
  if (row?.video_id && !row.video_id.startsWith('manual-')) {
    return `https://www.douyin.com/video/${row.video_id}`
  }
  return ''
}

function clearAutoResult() {
  auto.videos = []
  auto.checked = []
  auto.allChecked = false
  auto.message = ''
  auto.need_login = false
  syncAutoAccountLabel()
}

function syncAutoAccountLabel() {
  const found = douyinAccounts.value.find((a) => a.id === auto.account_id)
  auto.accountLabel = found ? found.name : ''
}

// -------------------------------------------------- 手动导入（隐藏 / 仅自己可见作品）
function openManualImport() {
  manual.form = {
    title: '', cover: '', tags: [],
    plays: 0, likes: 0, comments: 0, collects: 0, shares: 0, data_status: '正常'
  }
  manual.tagsText = ''
  manual.publishDate = Date.now()
  manual.visible = true
}

async function saveManualImport() {
  if (!manual.form.title.trim()) return ElMessage.warning('请填写视频名称')
  manual.saving = true
  try {
    const tags = manual.tagsText.split(/[,，]/).map((t) => t.trim().replace(/^#/, '')).filter(Boolean)
    // 手动导入的作品归属当前选中的账号标签，无需另选账号/平台
    const accountId = accountIdFromTab(selectedAccount.value)
    const account = douyinAccounts.value.find((a) => a.id === accountId)
      || douyinAccounts.value[0]
    // 手动作品没有真实 video_id，生成唯一标识用于去重；时间戳取发布时间或当前
    const ts = manual.publishDate ? Number(manual.publishDate) : Date.now()
    const videoId = `manual-${ts}-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`
    await api.post('/publish-stats/import-douyin', {
      videos: [{
        video_id: videoId,
        title: manual.form.title.trim(),
        cover: manual.form.cover,
        tags,
        plays: manual.form.plays,
        likes: manual.form.likes,
        comments: manual.form.comments,
        collects: manual.form.collects,
        shares: manual.form.shares,
        create_time: manual.publishDate ? Math.floor(ts / 1000) : null,
        account_id: account?.id || null,
        account_name: account?.name || '',
        data_status: manual.form.data_status
      }]
    }, { timeout: 120000 })
    ElMessage.success('已导入到发布数据表')
    manual.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    manual.saving = false
  }
}

// 页头「获取抖音数据」：只按当前单号获取，账号默认跟随当前账号标签，条数默认全部
function openAutoFetch() {
  auto.videos = []
  auto.checked = []
  auto.allChecked = false
  auto.message = ''
  auto.need_login = false
  auto.limit = 'all'
  auto.account_id = accountIdFromTab(selectedAccount.value) ?? douyinAccounts.value[0]?.id ?? null
  syncAutoAccountLabel()
  auto.visible = true
}

// 账号标签键 → 抖音账号 id；历史分组（name:）按名字匹配，匹配不到回落第一个单号
function accountIdFromTab(key) {
  if (key.startsWith('id:')) {
    const id = Number(key.slice(3))
    return douyinAccounts.value.some((a) => a.id === id) ? id : null
  }
  if (key.startsWith('name:')) {
    const name = key.slice(5)
    const found = douyinAccounts.value.find((a) => a.name === name)
    return found ? found.id : null
  }
  return null
}

function toggleAllAuto(checked) {
  auto.checked = auto.videos.map(() => !!checked)
}
function syncAutoAllChecked() {
  auto.allChecked = auto.videos.length > 0 && auto.checked.filter(Boolean).length === auto.videos.length
}

// '全部' 映射到浏览器采集上限 50 条
function resolveAutoLimit() {
  return auto.limit === 'all' ? 50 : Number(auto.limit) || 10
}

async function fetchDouyinList() {
  if (auto.loading) return
  if (!douyinAccounts.value.length) {
    return ElMessage.warning('请先到「我的账号」添加并登录抖音账号')
  }
  const targets = douyinAccounts.value.filter((a) => a.id === auto.account_id)
  if (!targets.length) return ElMessage.warning('请先选择一个抖音账号')

  auto.loading = true
  auto.videos = []
  auto.checked = []
  auto.allChecked = false
  auto.message = ''
  auto.need_login = false
  syncAutoAccountLabel()
  try {
    const { data } = await api.post(
      '/douyin/videos/fetch-all',
      { account_ids: targets.map((a) => a.id), limit: resolveAutoLimit() },
      { timeout: 300000 }
    )
    auto.videos = data.videos || []
    auto.checked = auto.videos.map((v) => !!(autoCheckImported.value && v.imported))
    auto.message = data.message || (data.ok ? '获取完成' : '获取失败')
    auto.need_login = !!data.need_login
    const reconciled = (data.accounts || []).reduce(
      (sum, a) => sum + (a.hidden || 0) + (a.restored || 0), 0)
    if (data.ok && auto.videos.length) {
      ElMessage.success(
        `已获取 ${auto.videos.length} 条作品` +
        (reconciled ? `，隐藏状态已同步 ${reconciled} 条` : '')
      )
      if (reconciled) await load()
    }
  } catch (e) {
    auto.message = e.response?.data?.detail || '获取失败'
  } finally {
    auto.loading = false
  }
}

// 兼容旧调用名
const doAutoFetch = fetchDouyinList

// 切换配置后即时同步当前列表的勾选状态
watch(autoCheckImported, (enabled) => {
  if (!auto.videos.length) return
  auto.checked = auto.videos.map((v) => !!(enabled && v.imported))
  syncAutoAllChecked()
})

// -------------------------------------------------- 抖音作品导入：直接写入发布数据表
function videoToImport(v) {
  return {
    video_id: v.video_id || '',
    title: v.title || '',
    cover: v.cover || '',
    tags: v.tags || [],
    plays: v.plays || 0,
    likes: v.likes || 0,
    comments: v.comments || 0,
    collects: v.collects || 0,
    shares: v.shares || 0,
    create_time: v.create_time || null,
    duration: v.duration || null,
    account_id: v.account_id || null,
    account_name: v.account_name || ''
  }
}

async function importVideos(videos) {
  const picked = videos || []
  if (!picked.length) return ElMessage.warning('请先勾选要导入的作品')
  if (auto.importingId || auto.batchImporting) return
  const isBatch = picked.length > 1
  if (isBatch) auto.batchImporting = true
  else auto.importingId = picked[0].video_id || picked[0].title || 'one'
  try {
    const { data } = await api.post(
      '/publish-stats/import-douyin',
      { videos: picked.map(videoToImport) },
      { timeout: 120000 }
    )
    ElMessage.success((data.message || '导入成功') + '，已写入发布数据表')
    auto.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '导入失败')
  } finally {
    auto.importingId = null
    auto.batchImporting = false
  }
}

function importOneVideo(v) {
  return importVideos([v])
}

// -------------------------------------------------- 点击「未配置」匹配待发布的创作记录
async function openMatchDialog(row) {
  matchDialog.importId = row.import_id
  matchDialog.row = row
  matchDialog.keyword = ''
  // 当前已关联记录置顶标记并默认选中
  matchDialog.currentId = row.production_id || null
  matchDialog.currentTitle = row.reference_title || ''
  matchDialog.currentCover = ''
  matchDialog.currentStatus = '已发布'
  matchDialog.currentOwner = row.owner_name || '未归属'
  matchDialog.productionId = matchDialog.currentId
  matchDialog.options = []
  matchDialog.loading = true
  matchDialog.visible = true
  try {
    const matchParams = { scope: scope.value }
    if (matchDialog.currentId) matchParams.exclude_production_id = matchDialog.currentId
    const [{ data: list }, detail] = await Promise.all([
      api.get('/publish-stats/match-options', { params: matchParams }),
      matchDialog.currentId
        ? api.get(`/productions/${matchDialog.currentId}`).catch(() => null)
        : Promise.resolve(null)
    ])
    if (detail?.data) {
      const p = detail.data
      matchDialog.currentTitle = p.title || matchDialog.currentTitle
      matchDialog.currentCover = p.cover || matchDialog.currentCover
      matchDialog.currentStatus = p.status || matchDialog.currentStatus
      matchDialog.currentOwner = p.owner_name || matchDialog.currentOwner
    }
    matchDialog.options = (list?.items || []).map((p) => ({
      id: p.id,
      title: p.title || '未命名视频',
      cover: p.cover || '',
      author: p.author || '',
      status: p.status || '',
      owner_name: p.owner_name || '',
      category_name: p.category_name || ''
    }))
  } catch (e) {
    matchDialog.options = []
    ElMessage.error(e.response?.data?.detail || '加载创作记录失败')
  } finally {
    matchDialog.loading = false
  }
}

async function confirmMatch() {
  if (!matchDialog.productionId) return ElMessage.warning('请选择一条创作记录')
  matchDialog.saving = true
  try {
    const { data } = await api.post(
      `/publish-stats/imports/${matchDialog.importId}/match`,
      { production_id: matchDialog.productionId }
    )
    ElMessage.success(`已匹配参考视频「${data.production_title || '创作记录'}」，记录状态已同步`)
    matchDialog.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '匹配失败')
  } finally {
    matchDialog.saving = false
  }
}

// 取消关联：创作记录回退「待发布」，来源创意状态同步回退
async function unmatchImport() {
  if (!matchDialog.currentId) return
  matchDialog.unmatching = true
  try {
    await api.post(`/publish-stats/imports/${matchDialog.importId}/unmatch`)
    ElMessage.success('已取消关联，创作记录状态已回退为待发布')
    matchDialog.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '取消关联失败')
  } finally {
    matchDialog.unmatching = false
  }
}

async function loadAccounts() {
  try {
    const { data } = await api.get('/publish-accounts')
    publishAccounts.value = Array.isArray(data) ? data : []
  } catch (e) {
    publishAccounts.value = []
  }
}

onMounted(async () => {
  await settings.load()
  await loadAccounts()
  await load()
  if (route.query.production_id) {
    const target = items.value.find((i) => i.production_id === Number(route.query.production_id))
    if (target) openRecord(target)
  }
})
</script>

<style scoped>
.account-tabs-card :deep(.el-card__body) {
  padding: 10px 14px;
}

.adm-tab-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.adm-tab-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 30px;
  padding: 0 12px;
  border: 1px solid var(--adm-border);
  border-radius: 16px;
  background: var(--adm-panel-soft);
  color: var(--adm-text-secondary);
  font-size: 12.5px;
  cursor: pointer;
  transition: background-color 0.15s ease, color 0.15s ease, border-color 0.15s ease;
}
.adm-tab-chip:hover {
  background: var(--adm-panel-hover);
}
.adm-tab-chip.is-active {
  background: var(--el-color-primary-light-9);
  color: var(--el-color-primary);
  border-color: var(--el-color-primary);
  font-weight: 600;
}
.adm-tab-avatar {
  width: 20px;
  height: 20px;
  border-radius: 50%;
  object-fit: cover;
  flex: 0 0 auto;
  border: 1px solid var(--adm-border);
}
.adm-tab-avatar.is-empty {
  display: grid;
  place-items: center;
  background: var(--adm-surface-sunken);
  color: var(--adm-text-placeholder);
  border-color: transparent;
}
.adm-status-bar {
  margin-top: 10px;
  padding-top: 10px;
  border-top: 1px solid var(--adm-border);
  align-items: center;
}
.adm-tab-chip--sm {
  height: 26px;
  padding: 0 10px;
  font-size: 12px;
}
.adm-tab-label {
  white-space: nowrap;
}
.adm-tab-count {
  font-size: 11px;
  opacity: 0.78;
  font-variant-numeric: tabular-nums;
}
.unrecorded-tip {
  margin-left: 6px;
  font-size: 11.5px;
  color: var(--adm-text-placeholder);
  white-space: nowrap;
}

/* 视频名称：封面 + 名称合并列 */
.pub-name-cell { display: flex; align-items: center; gap: 8px; width: 100%; min-width: 0; }
.pub-cover { width: 64px; height: 64px; border-radius: 10px; object-fit: cover; flex-shrink: 0; border: 1px solid var(--adm-border); }
.pub-cover.is-empty { display: grid; place-items: center; font-size: 10px; color: var(--adm-text-placeholder); background: var(--adm-panel-soft); }
.pub-name-main { flex: 1; min-width: 0; }
.pub-ref-name {
  display: inline-block;
  max-width: 100%;
  margin-top: 3px;
  font-size: 11.5px;
  color: var(--adm-text-secondary);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: middle;
}
.pub-ref-name.is-unset {
  color: var(--adm-coral);
  cursor: pointer;
  border-bottom: 1px dashed currentColor;
}
.pub-ref-name.is-clickable { cursor: pointer; }
.pub-ref-name.is-clickable:hover { color: var(--el-color-primary); }
.pub-ref-name.is-unset:hover { opacity: 0.78; }
.pub-ref-name.is-unset-static { color: var(--adm-text-placeholder); }
/* 视频名称第三行：@创作者 + 分类（未绑定显示「未配置」） */
.pub-ref-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
  min-width: 0;
  font-size: 11px;
  color: var(--adm-text-placeholder, #a8abb2);
  line-height: 1.4;
}
.pub-ref-author {
  max-width: 96px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: var(--adm-text-secondary);
}
.pub-ref-cat {
  max-width: 88px;
  min-width: 0;
  flex-shrink: 0;
}
.pub-ref-meta-unset { color: var(--adm-text-placeholder); }
.pub-title-link { color: inherit; text-decoration: none; }
.pub-title-link:hover { color: var(--el-color-primary); text-decoration: underline; }

/* 发布状态：上状态标签、下发布时间（同宽、小字） */
.pub-owner-cell {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  width: 100%;
}
.pub-status-tag {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 5px;
  box-sizing: border-box;
  width: 106px;
  height: 22px;
  padding: 0 6px;
  border-radius: 6px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
  white-space: nowrap;
}
.pub-status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.pub-status-tag.is-normal {
  background: rgba(108, 196, 154, 0.12);
  color: #4f9e78;
}
.pub-status-tag.is-normal .pub-status-dot { background: #6cc49a; box-shadow: 0 0 0 2px rgba(108, 196, 154, 0.16); }
.pub-status-tag.is-hidden {
  background: rgba(226, 138, 138, 0.12);
  color: #c26a6a;
}
.pub-status-tag.is-hidden .pub-status-dot { background: #e28a8a; box-shadow: 0 0 0 2px rgba(226, 138, 138, 0.16); }
.pub-owner-date {
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

/* 视频数据：时长 / 播放 / 点赞 / 评论 / 收藏 / 转发（两行三列） */
.video-stat {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
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
.video-stat-ico { display: inline-flex; align-items: center; justify-content: center; }
.video-stat-num { font-size: 12px; font-weight: 600; color: var(--adm-text-regular, #303133); }
.video-stat-item.is-duration .video-stat-ico { color: #7b8794; }
.video-stat-item.is-play .video-stat-ico { color: #4a7cc4; }
.video-stat-item.is-like .video-stat-ico { color: #e8474f; }
.video-stat-item.is-comment .video-stat-ico { color: #7b62c9; }
.video-stat-item.is-collect .video-stat-ico { color: #e6932c; }
.video-stat-item.is-share .video-stat-ico { color: #3da377; }

.metric-plays {
  color: #4a7cc4;
  font-weight: 600;
}

.metric-likes {
  color: #e05c4b;
  font-weight: 600;
}

.account-option {
  display: flex;
  align-items: center;
  gap: 8px;
}

.account-option-avatar {
  width: 22px;
  height: 22px;
  border-radius: 7px;
  object-fit: cover;
  flex-shrink: 0;
}

.account-option-name {
  color: var(--adm-text-primary);
}

.account-option-meta {
  margin-left: auto;
  font-size: 11.5px;
  color: var(--adm-text-placeholder);
}

/* 详情弹窗内表格贴边，通栏显示；表格自身承担横向滚动，避免滚动条冒到弹窗 body */
.detail-table-wrap {
  margin: 0 -20px;
  box-sizing: border-box;
  overflow-x: auto;
}
/* 弹窗 body 在 ≤1366px 下 padding 降为 16px，负边距同步收缩，避免通栏表格溢出 */
@media (max-width: 1366px) {
  .detail-table-wrap { margin: 0 -16px; }
}

.preview-player {
  width: 100%;
  max-height: 62vh;
  border-radius: 10px;
  background: #000;
}

@media (max-width: 768px) {
  :deep(.el-col) {
    max-width: 50%;
    flex: 0 0 50%;
  }
}

/* 自动采集 */
.auto-body { display: flex; flex-direction: column; gap: 14px; }
.auto-query { display: flex; align-items: center; gap: 10px; flex-wrap: wrap; }
.auto-config {
  padding: 10px 12px;
  border-radius: 10px;
  background: var(--adm-blue-bg, #eef4ff);
  font-size: 12.5px;
  color: var(--adm-text-regular);
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
}
.auto-build-time { font-size: 11.5px; color: var(--adm-text-placeholder); white-space: nowrap; }
.auto-tip { font-size: 12px; color: var(--adm-text-placeholder); margin-top: -8px; }
.auto-error {
  padding: 12px;
  border-radius: 10px;
  background: var(--adm-amber-bg, #fdf6ec);
  font-size: 13px;
  line-height: 1.6;
}
.auto-error-hint { color: var(--el-color-warning); margin-top: 4px; }
.auto-list-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 12.5px;
  font-weight: 600;
  color: var(--adm-text-regular);
}
.auto-check-all { display: inline-flex; align-items: center; gap: 8px; cursor: pointer; }
.auto-list-hint { font-size: 11.5px; font-weight: 400; color: var(--adm-text-placeholder); }
.auto-list { display: flex; flex-direction: column; gap: 8px; max-height: 52vh; overflow-y: auto; }
.auto-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 10px;
  border: 1px solid var(--adm-border);
  border-radius: 10px;
}
.auto-row-check { flex: 0 0 auto; margin-right: -4px; }
.auto-cover { width: 56px; height: 56px; object-fit: cover; border-radius: 8px; flex: 0 0 auto; }
.auto-cover.is-empty { opacity: 0.6; }
.auto-info { flex: 1; min-width: 0; }
.auto-title { font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.auto-imported-badge {
  margin-left: 8px;
  padding: 1px 6px;
  border-radius: 8px;
  background: var(--adm-green-bg, #eaf7ee);
  color: var(--adm-green, #2e9b5b);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
.auto-tags { margin-top: 4px; }
.auto-video-account {
  margin-left: 8px;
  padding: 1px 6px;
  border-radius: 8px;
  background: var(--adm-coral-bg);
  color: var(--adm-coral);
  font-size: 11px;
  font-weight: 500;
  white-space: nowrap;
}
.auto-nums { margin-top: 4px; font-size: 12px; color: var(--adm-text-secondary); }
.auto-empty { padding: 32px 0; text-align: center; color: var(--adm-text-placeholder); font-size: 13px; }

/* 手动关联弹窗 */
.batch-cover { width: 46px; height: 46px; border-radius: 8px; object-fit: cover; flex: 0 0 auto; border: 1px solid var(--adm-border); }
.batch-cover.is-empty { display: grid; place-items: center; color: var(--adm-text-placeholder); background: var(--adm-surface-sunken); }
.batch-video-info { min-width: 0; flex: 1; }
.batch-title { font-size: 13px; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* 手动导入弹窗 */
.manual-body { max-height: 62vh; overflow-y: auto; padding-right: 4px; }
.manual-metrics { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px 12px; width: 100%; }
.manual-metrics label { display: flex; align-items: center; gap: 6px; font-size: 12px; color: var(--adm-text-secondary); }
.manual-metrics :deep(.el-input-number) { flex: 1; min-width: 0; }

.match-body { display: flex; flex-direction: column; gap: 12px; flex: 1; min-height: 0; box-sizing: border-box; }
.match-source { display: flex; align-items: center; gap: 10px; padding: 10px; border: 1px solid var(--adm-border); border-radius: 10px; background: var(--adm-panel-soft); }
.match-search { width: 100%; }
/* 列表区独立滚动：弹窗整体限高后，头部与底部按钮常驻，只保留这一条滚动条 */
.match-options { display: flex; flex-direction: column; gap: 8px; padding-right: 4px; flex: 1; min-height: 0; box-sizing: border-box; overflow-y: auto; overscroll-behavior: contain; }
.match-option-tags { display: flex; align-items: center; gap: 6px; flex-wrap: wrap; margin-top: 4px; }
.match-owner-tag { font-size: 11px; height: 20px; line-height: 18px; }
.match-option-author { font-size: 12px; color: var(--adm-text-secondary); white-space: nowrap; }
.match-category-badge { max-width: 120px; min-width: 0; flex-shrink: 0; }
.match-option {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px; cursor: pointer;
  border: 1px solid var(--adm-border); border-radius: 10px; background: var(--adm-panel-soft);
}
.match-option:hover { border-color: var(--el-color-primary); }
.match-option.is-active { border-color: var(--el-color-primary); background: var(--el-color-primary-light-9); }
.match-option.is-current { border-color: var(--el-color-success); background: var(--el-color-success-light-9); }
.match-option.is-current.is-active { border-color: var(--el-color-success); background: var(--el-color-success-light-9); }
.match-current-badge {
  display: inline-block; margin-left: 6px; padding: 1px 6px; border-radius: 4px;
  background: var(--el-color-success); color: #fff; font-size: 10px; font-weight: 600; vertical-align: middle;
}
.match-option-cover { width: 40px; height: 40px; border-radius: 6px; object-fit: cover; flex: 0 0 auto; border: 1px solid var(--adm-border); }
.match-option-cover.is-empty { display: grid; place-items: center; color: var(--adm-text-placeholder); background: var(--adm-surface-sunken); }
.match-option-info { flex: 1; min-width: 0; }
.match-check { color: var(--el-color-primary); font-size: 18px; }
</style>
