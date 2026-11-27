<template>
  <div class="stack">
    <PageHeader
      :icon="VideoCamera"
      title="视频创作"
      tone="lilac"
      desc="第二步 · 选择人物 / 场景 / 服装资产、创作平台与提示词；完成后状态更新为已发布"
    >
      <template #extra>
        <el-input v-model="keyword" placeholder="搜索名称" clearable style="width: 180px" @keyup.enter="load">
          <template #prefix><el-icon><Search /></el-icon></template>
        </el-input>
        <el-select v-model="platform" placeholder="创作平台" clearable style="width: 130px" @change="load">
          <el-option v-for="p in settings.platformOptions" :key="p.name" :label="p.name" :value="p.name">
            <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
          </el-option>
        </el-select>
        <el-select v-model="scope" style="width: 120px" @change="load">
          <el-option value="all" label="全部成员" />
          <el-option value="mine" label="仅我的" />
        </el-select>
        <el-button
          v-if="perm.can('productions.create')"
          type="primary"
          :icon="Plus"
          @click="openCreate"
        >新增创作</el-button>
      </template>
    </PageHeader>

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
        <el-table :data="pagedList" stripe style="width: 100%" empty-text="还没有创作记录，可点右上角「新增创作」">
          <!-- 封面 + 参考视频（第二行作者 + 类别） -->
          <el-table-column label="封面" width="72" align="center">
            <template #default="{ row }">
              <div class="adm-cell-cover">
                <img
                  v-if="row.cover"
                  :src="row.cover"
                  class="adm-cover-thumb"
                  :alt="row.title"
                  :title="hasReferenceVideo(row) ? '参考视频封面' : '默认封面（无参考视频）'"
                />
                <img v-else src="/placeholder.svg" class="adm-cover-thumb is-empty" alt="暂无封面" />
              </div>
            </template>
          </el-table-column>

          <el-table-column label="参考视频" min-width="180" align="left">
            <template #default="{ row }">
              <a
                v-if="row.douyin_url"
                :href="row.douyin_url"
                target="_blank"
                rel="noopener"
                class="adm-cell-link adm-cell-text adm-cell-text--clamp2"
                :title="(row.title || '未命名制作') + ' · 点击打开抖音'"
              >{{ row.title || '未命名制作' }}</a>
              <span v-else class="adm-cell-text adm-cell-text--clamp2" :title="row.title || '未命名制作'">
                {{ row.title || '未命名制作' }}
              </span>
              <div class="adm-cell-sub">
                <span
                  class="idea-author"
                  :title="hasReferenceVideo(row) ? (row.author || '未获取作者') : '无参考视频创作'"
                >@{{ hasReferenceVideo(row) ? (row.author || '未获取') : '无参考视频创作' }}</span>
                <OptionBadge
                  v-if="row.category_name"
                  :name="row.category_name"
                  :color="settings.option('category', row.category_name).color"
                  :image="settings.option('category', row.category_name).image"
                  :display="settings.option('category', row.category_name).display"
                />
                <span v-else class="adm-cell-empty">—</span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="人物模型" min-width="124" align="left">
            <template #default="{ row }">
              <div v-if="row.characters && row.characters.length" class="char-cell">
                <el-image
                  v-for="c in row.characters.slice(0, 3)"
                  :key="c.id"
                  :src="c.character_cover || '/placeholder.svg'"
                  fit="cover"
                  class="char-avatar"
                  :title="c.character_name + (c.role ? ' · ' + c.role : '')"
                >
                  <template #error><img src="/placeholder.svg" class="char-avatar" alt="暂无资产" /></template>
                </el-image>
              </div>
              <div v-else class="char-cell">
                <img src="/placeholder.svg" class="char-avatar is-empty" alt="未绑定人物模型" title="未绑定人物模型" />
              </div>
            </template>
          </el-table-column>

          <el-table-column label="创作平台" min-width="100" align="center">
            <template #default="{ row }">
              <OptionBadge
                v-if="row.platform"
                :name="row.platform"
                :color="settings.option('platform', row.platform).color"
                :image="settings.option('platform', row.platform).image"
                :display="settings.option('platform', row.platform).display"
              />
              <span v-else class="adm-cell-empty">—</span>
            </template>
          </el-table-column>

          <el-table-column label="状态" min-width="100" align="center">
            <template #default="{ row }">
              <button
                type="button"
                class="prod-status-btn"
                :disabled="!canChangeStatus(row) || !['制作中', '待发布', '废弃'].includes(row.status)"
                :title="statusClickTitle(row)"
                @click="openStatusConfirm(row)"
              >
                <el-tag :type="productionStatusType(row.status)" size="small" effect="light">{{ productionStatusLabel(row.status) }}</el-tag>
              </button>
            </template>
          </el-table-column>

          <el-table-column label="创作时间" min-width="140" align="left">
            <template #default="{ row }">
              <div class="prod-time-cell">
                <span class="prod-time-row is-start">
                  <el-icon :size="12"><VideoPlay /></el-icon>
                  <span>开始</span>
                  <span class="adm-cell-time">{{ row.produced_at ? formatDate(row.produced_at) : '—' }}</span>
                </span>
                <span class="prod-time-row is-done">
                  <el-icon :size="12"><CircleCheckFilled /></el-icon>
                  <span>完成</span>
                  <span class="adm-cell-time">{{ row.completed_at ? formatDate(row.completed_at) : '—' }}</span>
                </span>
              </div>
            </template>
          </el-table-column>

          <el-table-column label="创作人" min-width="96" align="center">
            <template #default="{ row }">
              <el-tag size="small" effect="plain" :type="row.is_owner ? 'primary' : 'info'">
                {{ row.owner_name }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="提示词" min-width="92" align="left">
            <template #default="{ row }">
              <span v-if="promptToText(row.prompt)" class="prompt-cell">{{ promptToText(row.prompt) }}</span>
              <span v-else class="adm-cell-empty">—</span>
            </template>
          </el-table-column>

          <el-table-column label="操作" min-width="120" fixed="right" align="center">
            <template #default="{ row }">
              <div class="adm-cell-actions">
                <el-button v-if="perm.can('productions.edit')" type="text" size="small" @click="openEdit(row)">编辑</el-button>
                <el-button v-if="perm.can('productions.delete')" type="text" size="small" class="danger-text" @click="remove(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :image-size="100" description="还没有创作记录" />
          </template>
        </el-table>
      </div>

      <AppPagination v-model:page="page" :total="list.length" v-model:page-size="PAGE_SIZE" />
    </el-card>

    <!-- 新建弹窗：无参考视频，手动创建创作记录 -->
    <el-dialog
      v-model="create.visible"
      width="640px"
      class="adm-dialog-detail edit-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <DialogHeader
          :icon="VideoCamera"
          title="新增视频创作"
          sub="无参考视频 · 封面使用默认图"
          tone="lilac"
        />
      </template>
      <div class="edit-dialog-body" v-loading="create.loading">
        <el-form label-width="96px" label-position="right">
          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-primary" />基础信息</h4>
            <el-form-item label="视频名称" required>
              <el-input v-model="create.form.title" placeholder="请输入视频名称" maxlength="200" />
            </el-form-item>
            <el-form-item label="类型" required>
              <el-select v-model="create.form.category_id" placeholder="选择视频分类" clearable filterable style="width: 100%">
                <el-option v-for="c in settings.categoryOptions" :key="c.id" :label="c.name" :value="c.id">
                  <OptionBadge :name="c.name" :color="c.color" :image="c.image" :display="c.display" />
                </el-option>
              </el-select>
            </el-form-item>
          </section>

          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-mint" />制作信息</h4>
            <el-form-item label="人物模型" required>
              <el-select
                v-model="create.form.characterIds"
                multiple
                filterable
                clearable
                style="width: 100%"
                placeholder="选择人物模型（可多选）"
              >
                <el-option v-for="a in characterOptions" :key="a.id" :label="a.name" :value="a.id" />
              </el-select>
            </el-form-item>
            <el-form-item label="创作平台" required>
              <el-select v-model="create.form.platform" placeholder="选择平台" clearable filterable style="width: 100%">
                <el-option v-for="p in settings.platformOptions" :key="p.name" :label="p.name" :value="p.name">
                  <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="提示词" required>
              <el-input
                v-model="create.form.promptText"
                type="textarea"
                :rows="5"
                maxlength="2500"
                show-word-limit
                placeholder="输入完整提示词（最多 2500 字）"
                class="prompt-textarea"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="create.form.remark" type="textarea" :rows="2" placeholder="补充说明" />
            </el-form-item>
          </section>
        </el-form>

        <div class="edit-dialog-footer">
          <el-button type="primary" plain @click="create.visible = false">取消</el-button>
          <el-button type="primary" :loading="create.saving" @click="doCreate">创建</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 编辑弹窗：直接编辑制作字段，无需跳转详情页 -->
    <el-dialog
      v-model="edit.visible"
      width="640px"
      class="adm-dialog-detail edit-dialog"
      :close-on-click-modal="false"
      destroy-on-close
    >
      <template #header>
        <DialogHeader
          :icon="VideoCamera"
          :title="edit.form.title || '编辑制作'"
          sub="视频创作 · 直接修改字段后保存"
          tone="lilac"
        />
      </template>

      <div class="edit-dialog-body" v-loading="edit.loading">
        <el-form label-width="96px" label-position="right">
          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-primary" />参考视频</h4>
            <div class="ref-video-view">
              <img v-if="edit.form.cover" :src="edit.form.cover" class="ref-cover" alt="参考视频封面" />
              <img v-else src="/placeholder.svg" class="ref-cover is-empty" alt="暂无封面" />
              <div class="ref-video-info">
                <a
                  v-if="edit.form.douyin_url"
                  :href="edit.form.douyin_url"
                  target="_blank"
                  rel="noopener"
                  class="ref-title ref-title-link"
                  :title="`点击打开抖音：${edit.form.title || '未命名视频'}`"
                >{{ edit.form.title || '未命名视频' }}</a>
                <div v-else class="ref-title">{{ edit.form.title || '未命名视频' }}</div>
                <TagCell :tags="edit.form.tags || []" :max-lines="1" />
                <!-- 只读项：类型 / 制作人 / 状态，放在参考视频卡片内，不带小标题 -->
                <div class="readonly-row">
                  <div class="readonly-item">
                    <OptionBadge
                      v-if="categoryName(edit.form.category_id)"
                      :name="categoryName(edit.form.category_id)"
                      :color="settings.option('category', categoryName(edit.form.category_id)).color"
                      :image="settings.option('category', categoryName(edit.form.category_id)).image"
                      :display="settings.option('category', categoryName(edit.form.category_id)).display"
                    />
                    <span v-else class="adm-cell-empty">—</span>
                  </div>
                  <div class="readonly-item">
                    <el-tag size="small" effect="plain">{{ edit.form.ownerName || '未指定' }}</el-tag>
                  </div>
                  <div class="readonly-item">
                    <el-tag :type="productionStatusType(edit.form.status)" size="small" effect="light">{{ productionStatusLabel(edit.form.status) }}</el-tag>
                  </div>
                </div>
              </div>
            </div>
          </section>

          <section class="adm-drawer-section">
            <h4 class="adm-drawer-section-title"><span class="adm-drawer-bar is-mint" />制作信息</h4>
            <el-form-item label="人物模型">
              <div class="model-selected-list">
                <div v-for="a in selectedEditCharacters" :key="a.id" class="model-selected-item" :title="a.name">
                  <el-image :src="characterCover(a)" fit="cover" class="model-selected-cover">
                    <template #error><img src="/placeholder.svg" class="model-selected-cover" alt="" /></template>
                  </el-image>
                  <span class="model-selected-name">{{ a.name }}</span>
                  <button type="button" class="model-remove" title="删除该人物模型" @click="removeEditCharacter(a.id)">×</button>
                </div>
                <button type="button" class="model-add" @click="openAssetPicker">
                  <el-icon><Plus /></el-icon>选择人物模型
                </button>
              </div>
            </el-form-item>
            <el-form-item label="创作平台">
              <el-select v-model="edit.form.platform" placeholder="选择平台" clearable filterable style="width: 100%">
                <template v-if="edit.form.platform" #prefix>
                  <OptionBadge
                    :name="edit.form.platform"
                    :color="settings.option('platform', edit.form.platform).color"
                    :image="settings.option('platform', edit.form.platform).image"
                    display="icon"
                    :size="16"
                  />
                </template>
                <el-option v-for="p in settings.platformOptions" :key="p.name" :label="p.name" :value="p.name">
                  <OptionBadge :name="p.name" :color="p.color" :image="p.image" :display="p.display" />
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="提示词">
              <el-input
                v-model="edit.form.promptText"
                type="textarea"
                :rows="5"
                maxlength="2500"
                show-word-limit
                placeholder="输入完整提示词（最多 2500 字）"
                class="prompt-textarea"
              />
            </el-form-item>
            <el-form-item label="备注">
              <el-input v-model="edit.form.remark" type="textarea" :rows="2" placeholder="补充说明" />
            </el-form-item>
          </section>
        </el-form>

        <div class="edit-dialog-footer">
          <el-button type="primary" plain @click="edit.visible = false">取消</el-button>
          <el-button type="primary" :loading="edit.saving" @click="doEdit">保存</el-button>
        </div>
      </div>
    </el-dialog>

    <!-- 人物模型选择：展示全部人物资产，点击选中/取消，确定后写回编辑表单 -->
    <el-dialog
      v-model="assetPicker.visible"
      title="选择人物模型"
      width="760px"
      class="adm-dialog-detail model-picker-dialog"
      append-to-body
      :close-on-click-modal="false"
      destroy-on-close
    >
      <div class="model-picker-grid">
        <button
          v-for="a in characterOptions"
          :key="a.id"
          type="button"
          class="model-picker-item"
          :class="{ 'is-selected': assetPicker.selected.includes(a.id) }"
          :title="a.name"
          @click="toggleAssetPicker(a.id)"
        >
          <el-image :src="characterCover(a)" fit="cover" class="model-picker-cover">
            <template #error><img src="/placeholder.svg" class="model-picker-cover" alt="" /></template>
          </el-image>
          <span class="model-picker-name">{{ a.name }}</span>
          <span v-if="assetPicker.selected.includes(a.id)" class="model-picker-check"><el-icon><CircleCheckFilled /></el-icon></span>
        </button>
      </div>
      <div v-if="!characterOptions.length" class="model-picker-empty">暂无人物资产，请先在「人物资产」页面添加。</div>
      <template #footer>
        <el-button plain @click="assetPicker.visible = false">取消</el-button>
        <el-button type="primary" @click="confirmAssetPicker">确定（{{ assetPicker.selected.length }}）</el-button>
      </template>
    </el-dialog>

    <!-- 状态确认：制作中确认完成→待发布；待发布确认还原→制作中 -->
    <ConfirmDialog
      v-model="statusConfirm.visible"
      :title="statusConfirm.title"
      :message="statusConfirm.message"
      :loading="statusConfirm.loading"
      :confirm-text="statusConfirm.confirmText"
      :variant="statusConfirm.variant"
      :icon="statusConfirm.icon"
      @confirm="doChangeStatus"
    />

    <!-- 待发布→返工 / 废弃：参考编辑弹窗展示创意视频 -->
    <el-dialog
      v-model="statusChoice.visible"
      title="待发布视频处理"
      width="520px"
      class="adm-dialog-detail status-choice-dialog"
      :close-on-click-modal="false"
      append-to-body
    >
      <div class="status-choice-body">
        <div class="status-choice-label">创意视频</div>
        <div class="complete-ref-video">
          <img
            v-if="statusChoice.row?.cover"
            :src="statusChoice.row.cover"
            class="complete-ref-cover"
            alt="创意视频封面"
          />
          <img v-else src="/placeholder.svg" class="complete-ref-cover is-empty" alt="暂无封面" />
          <div class="complete-ref-info">
            <div class="complete-ref-title">{{ statusChoice.row?.title || '未命名视频' }}</div>
            <TagCell :tags="statusChoice.row?.tags || []" :max-lines="1" />
            <div class="complete-ref-readonly">
              <OptionBadge
                v-if="statusChoice.row?.category_name"
                :name="statusChoice.row.category_name"
                :color="settings.option('category', statusChoice.row.category_name).color"
                :image="settings.option('category', statusChoice.row.category_name).image"
                :display="settings.option('category', statusChoice.row.category_name).display"
              />
              <span v-else class="adm-cell-empty">—</span>
              <el-tag size="small" effect="plain">{{ statusChoice.row?.owner_name || '未指定' }}</el-tag>
              <el-tag :type="productionStatusType(statusChoice.row?.status)" size="small" effect="light">
                {{ productionStatusLabel(statusChoice.row?.status) }}
              </el-tag>
            </div>
          </div>
        </div>
        <p class="status-choice-tip">视频已制作完成，等待确认；若需修改制作请选择「返工」，若题材废弃请选择「废弃」。废弃后可再点状态还原为待发布。</p>
      </div>
      <template #footer>
        <el-button @click="statusChoice.visible = false">取消</el-button>
        <el-button type="danger" plain :loading="statusChoice.loading" @click="doStatusChoice('废弃')">废弃</el-button>
        <el-button type="primary" :loading="statusChoice.loading" @click="doStatusChoice('制作中')">返工</el-button>
      </template>
    </el-dialog>

    <!-- 制作中→确认完成：选择完成时间（默认今天，只选日期） -->
    <el-dialog
      v-model="completeDialog.visible"
      title="确认完成制作"
      width="420px"
      :close-on-click-modal="false"
      append-to-body
      class="complete-dialog"
    >
      <div class="complete-body">
        <div class="complete-ref-video">
          <img
            v-if="completeDialog.row?.cover"
            :src="completeDialog.row.cover"
            class="complete-ref-cover"
            alt="参考视频封面"
          />
          <img v-else src="/placeholder.svg" class="complete-ref-cover is-empty" alt="暂无封面" />
          <div class="complete-ref-info">
            <div class="complete-ref-title">{{ completeDialog.row?.title || '未命名视频' }}</div>
            <TagCell :tags="completeDialog.row?.tags || []" :max-lines="1" />
            <div class="complete-ref-readonly">
              <OptionBadge
                v-if="completeDialog.row?.category_name"
                :name="completeDialog.row.category_name"
                :color="settings.option('category', completeDialog.row.category_name).color"
                :image="settings.option('category', completeDialog.row.category_name).image"
                :display="settings.option('category', completeDialog.row.category_name).display"
              />
              <span v-else class="adm-cell-empty">—</span>
              <el-tag size="small" effect="plain">{{ completeDialog.row?.owner_name || '未指定' }}</el-tag>
              <el-tag :type="productionStatusType(completeDialog.row?.status)" size="small" effect="light">
                {{ productionStatusLabel(completeDialog.row?.status) }}
              </el-tag>
            </div>
          </div>
        </div>
        <div class="complete-field">
          <label>完成日期</label>
          <el-date-picker
            v-model="completeDialog.date"
            type="date"
            value-format="YYYY-MM-DD"
            placeholder="选择完成日期"
            :disabled-date="disableFutureDate"
            style="width: 100%"
          />
        </div>
        <p class="complete-tip">默认今天，可修改为实际完成日期；时间部分不计入统计。</p>
      </div>
      <template #footer>
        <el-button @click="completeDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="completeDialog.loading" @click="doCompleteProduction">确认完成</el-button>
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
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheckFilled, Loading, Plus, Search, Timer, VideoCamera, VideoPlay, Warning } from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import AppPagination from '../components/ui/AppPagination.vue'
import ConfirmDialog from '../components/ui/ConfirmDialog.vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import OptionBadge from '../components/ui/OptionBadge.vue'
import StatCard from '../components/ui/StatCard.vue'
import TagCell from '../components/ui/TagCell.vue'
import { api, formatDate, productionStatusLabel, productionStatusType } from '../api'
import { useAuthStore } from '../stores/auth'
import { usePermissionStore } from '../stores/permission'
import { useSettingsStore } from '../stores/settings'

const auth = useAuthStore()
const perm = usePermissionStore()
const settings = useSettingsStore()
const router = useRouter()

const PAGE_SIZE = ref(12)

const loading = ref(false)
const list = ref([])
const keyword = ref('')
const platform = ref('')
const scope = ref('all')
const page = ref(1)
const characterOptions = ref([])
const confirm = reactive({ visible: false, loading: false, title: '', message: '', id: null })
const statusConfirm = reactive({
  visible: false, loading: false, row: null, target: '',
  title: '', message: '', confirmText: '', variant: 'success', icon: 'success'
})
// 待发布→返工 / 废弃：底部两个按钮直接决定目标状态
const statusChoice = reactive({ visible: false, loading: false, row: null })
// 制作中→待发布：选择完成日期（默认今天）
const completeDialog = reactive({ visible: false, loading: false, row: null, date: '' })

function todayString() {
  const d = new Date()
  const p = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`
}
// 完成日期不能晚于今天（不能提前完成）：禁用今天之后的所有日期
function disableFutureDate(date) {
  const now = new Date()
  now.setHours(23, 59, 59, 999)
  return date.getTime() > now.getTime()
}
// 五项统计：内部「废弃 / 已完成」展示为「已废弃 / 已发布」
const counts = computed(() => {
  const all = list.value
  return {
    total: all.length,
    making: all.filter((i) => i.status === '制作中').length,
    pending: all.filter((i) => i.status === '待发布').length,
    abandoned: all.filter((i) => i.status === '废弃').length,
    published: all.filter((i) => i.status === '已完成').length
  }
})

const statCards = computed(() => [
  { label: '创作总量', value: counts.value.total, icon: VideoCamera, tone: 'blue' },
  { label: '制作中', value: counts.value.making, icon: Loading, tone: 'lilac' },
  { label: '待发布', value: counts.value.pending, icon: Timer, tone: 'amber' },
  { label: '已废弃', value: counts.value.abandoned, icon: Warning, tone: 'amber' },
  { label: '已发布', value: counts.value.published, icon: CircleCheckFilled, tone: 'mint' }
])

const edit = reactive({
  visible: false, loading: false, saving: false, id: null,
  form: emptyEditForm()
})
const create = reactive({
  visible: false, loading: false, saving: false,
  form: emptyCreateForm()
})

function emptyCreateForm() {
  return {
    title: '', category_id: null, characterIds: [], platform: '',
    promptText: '', remark: ''
  }
}

function emptyEditForm() {
  return {
    title: '', cover: '', tags: [], douyin_url: '', category_id: null,
    characterIds: [], platform: '', promptText: '',
    owner_id: null, ownerName: '', status: '制作中', remark: ''
  }
}

// 分段提示词 → 单段文字（兼容历史数据：多段用换行拼接）
function promptToText(prompt) {
  if (!prompt || !prompt.length) return ''
  return prompt.map((p) => p.text || '').filter(Boolean).join('\n').slice(0, 2500)
}

function categoryName(id) {
  if (!id) return ''
  const c = settings.categoryOptions.find((x) => x.id === id)
  return c ? c.name : ''
}

// 区分「由参考视频创建」与「新增创作（无参考视频）」
function hasReferenceVideo(row) {
  return !!(row.idea_id || row.douyin_url)
}

// 新增创作：弹窗不展示封面/作者/创作人，保存时自动生成默认封面、当前登录作者与创作人、开始时间=提交时间
function openCreate() {
  Object.assign(create.form, emptyCreateForm())
  create.visible = true
}

async function doCreate() {
  const f = create.form
  if (!f.title.trim()) return ElMessage.warning('请填写视频名称')
  if (!f.category_id) return ElMessage.warning('请选择类型')
  if (!f.characterIds.length) return ElMessage.warning('请选择人物模型')
  if (!f.platform) return ElMessage.warning('请选择创作平台')
  if (!f.promptText.trim()) return ElMessage.warning('请填写提示词')
  create.saving = true
  try {
    const payload = {
      title: f.title.trim(),
      cover: '/placeholder.svg',
      author: auth.displayName,
      category_id: f.category_id,
      platform: f.platform,
      prompt: [{ seg: '', text: f.promptText.trim() }],
      status: '制作中',
      remark: f.remark,
      characters: f.characterIds.map((id, i) => ({ character_id: id, role: i === 0 ? '主角' : '配角', sort: i }))
    }
    await api.post('/productions', payload)
    ElMessage.success('创建成功，已进入制作中')
    create.visible = false
    await load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    create.saving = false
  }
}

// 客户端分页
const pagedList = computed(() => {
  const start = (page.value - 1) * PAGE_SIZE.value
  return list.value.slice(start, start + PAGE_SIZE.value)
})

async function load() {
  loading.value = true
  try {
    // 展示全部创作记录，四项统计直接由当前可见范围计算
    const { data } = await api.get('/productions', {
      params: { keyword: keyword.value, platform: platform.value, scope: scope.value, page_size: 200 }
    })
    list.value = data.items || []
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败，请重试')
  } finally {
    loading.value = false
  }
}

async function loadCharacters() {
  try {
    const { data } = await api.get('/characters', { params: { scope: 'all' } })
    characterOptions.value = (data || []).filter((a) => (a.asset_type || 'character') === 'character')
  } catch (e) {
    characterOptions.value = []
  }
}

/* 人物模型：资产封面取第一张人物图片，缺失时用默认图 */
function characterCover(asset) {
  return asset?.images?.[0]?.file_path || asset?.cover || '/placeholder.svg'
}

const selectedEditCharacters = computed(() =>
  characterOptions.value.filter((a) => edit.form.characterIds.includes(a.id))
)

const assetPicker = reactive({ visible: false, selected: [] })

function openAssetPicker() {
  assetPicker.selected = [...edit.form.characterIds]
  assetPicker.visible = true
}

function toggleAssetPicker(id) {
  const idx = assetPicker.selected.indexOf(id)
  if (idx >= 0) assetPicker.selected.splice(idx, 1)
  else assetPicker.selected.push(id)
}

function confirmAssetPicker() {
  edit.form.characterIds = [...assetPicker.selected]
  assetPicker.visible = false
}

function removeEditCharacter(id) {
  edit.form.characterIds = edit.form.characterIds.filter((x) => x !== id)
}

// 制作中/待发布/废弃状态可点击流转；拥有「编辑制作」权限即可，不再限定归属人
function canChangeStatus(row) {
  return perm.can('productions.edit')
}

function statusClickTitle(row) {
  if (!canChangeStatus(row)) return '需要有编辑制作权限'
  if (row.status === '制作中') return '点击确认完成并进入待发布'
  if (row.status === '待发布') return '点击选择返工或废弃'
  if (row.status === '废弃') return '点击确认还原为待发布'
  return `${productionStatusLabel(row.status)}（已关联发布数据，状态不可修改）`
}

// 制作中→待发布前的信息完整性校验：创作平台 + 提示词内容必填
function missingProductionInfo(row) {
  const missing = []
  if (!row.platform) missing.push('创作平台')
  const promptText = (row.prompt || []).map((p) => p.text || '').join('').trim()
  if (!promptText) missing.push('提示词')
  return missing
}

// 制作中点状态：确认完成→待发布；待发布点状态：返工/废弃；废弃点状态：还原为待发布
function openStatusConfirm(row) {
  if (!canChangeStatus(row)) return
  if (row.status === '制作中') {
    const missing = missingProductionInfo(row)
    if (missing.length) {
      ElMessage.warning(`请先补全制作信息：${missing.join('、')}，再确认完成`)
      return
    }
    // 制作中→待发布：弹窗选择完成日期（默认今天）
    completeDialog.row = row
    completeDialog.date = todayString()
    completeDialog.visible = true
    return
  } else if (row.status === '待发布') {
    // 待发布→返工 / 废弃，两个按钮直接决定目标状态
    statusChoice.row = row
    statusChoice.visible = true
    return
  } else if (row.status === '废弃') {
    statusConfirm.target = '待发布'
    statusConfirm.title = '还原为待发布'
    statusConfirm.message = `确定将「${row.title || '该视频'}」从已废弃还原为「待发布」吗？`
    statusConfirm.confirmText = '确认还原'
    statusConfirm.variant = 'warning'
    statusConfirm.icon = 'warning'
  } else {
    return
  }
  statusConfirm.row = row
  statusConfirm.visible = true
}

async function doChangeStatus() {
  const row = statusConfirm.row
  if (!row) return
  statusConfirm.loading = true
  try {
    const { data } = await api.put(`/productions/${row.id}`, { status: statusConfirm.target })
    row.status = data.status
    row.produced_at = data.produced_at
    row.completed_at = data.completed_at
    ElMessage.success(`状态已改为「${productionStatusLabel(data.status)}」`)
    statusConfirm.visible = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '状态修改失败')
  } finally {
    statusConfirm.loading = false
  }
}

// 待发布选择「返工 / 废弃」后写入状态
async function doStatusChoice(target) {
  const row = statusChoice.row
  if (!row) return
  statusChoice.loading = true
  try {
    const { data } = await api.put(`/productions/${row.id}`, { status: target })
    row.status = data.status
    row.produced_at = data.produced_at
    row.completed_at = data.completed_at
    ElMessage.success(`状态已改为「${productionStatusLabel(data.status)}」`)
    statusChoice.visible = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '状态修改失败')
  } finally {
    statusChoice.loading = false
  }
}

// 制作中确认完成：把所选日期（当天 23:59:59）作为完成时间写入，状态改为待发布
async function doCompleteProduction() {
  const row = completeDialog.row
  if (!row) return
  if (!completeDialog.date) {
    ElMessage.warning('请选择完成日期')
    return
  }
  if (completeDialog.date > todayString()) {
    ElMessage.warning('完成日期不能晚于今天，不能提前完成')
    return
  }
  completeDialog.loading = true
  try {
    const completedAt = `${completeDialog.date}T23:59:59`
    const { data } = await api.put(`/productions/${row.id}`, {
      status: '待发布', completed_at: completedAt
    })
    row.status = data.status
    row.produced_at = data.produced_at
    row.completed_at = data.completed_at
    ElMessage.success(`状态已改为「${data.status}」`)
    completeDialog.visible = false
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '状态修改失败')
  } finally {
    completeDialog.loading = false
  }
}

async function openEdit(row) {
  edit.id = row.id
  edit.loading = true
  edit.form = emptyEditForm()
  edit.visible = true
  try {
    const { data } = await api.get(`/productions/${row.id}`)
    Object.assign(edit.form, {
      title: data.title || '',
      cover: data.cover || '',
      tags: [...(data.tags || [])],
      douyin_url: data.douyin_url || '',
      category_id: data.category_id || null,
      characterIds: (data.characters || []).map((c) => c.character_id),
      platform: data.platform || '',
      promptText: promptToText(data.prompt),
      owner_id: data.owner_id || null,
      ownerName: data.owner_name || '未指定',
      status: data.status || '制作中',
      remark: data.remark || ''
    })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载详情失败')
  } finally {
    edit.loading = false
  }
}

async function doEdit() {
  edit.saving = true
  try {
    // 参考视频信息 / 制作人 / 状态均为只读，不再提交，仅保存可编辑的制作字段
    const payload = {
      platform: edit.form.platform,
      prompt: [{ seg: '', text: edit.form.promptText }],
      remark: edit.form.remark,
      characters: edit.form.characterIds.map((id, i) => ({ character_id: id, role: i === 0 ? '主角' : '配角', sort: i }))
    }
    await api.put(`/productions/${edit.id}`, payload)
    ElMessage.success('已保存')
    edit.visible = false
    load()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    edit.saving = false
  }
}

function remove(row) {
  confirm.title = '删除制作记录'
  confirm.message = `确定删除「${row.title || '未命名制作'}」吗？删除后无法恢复。`
  confirm.id = row.id
  confirm.visible = true
}

async function doRemove() {
  confirm.loading = true
  try {
    await api.delete(`/productions/${confirm.id}`)
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
  await settings.load()
  await loadCharacters()
  load()
})
</script>

<style scoped>
/* 状态按钮：制作中/待发布可点击确认流转 */
.prod-status-btn {
  display: inline-flex;
  align-items: center;
  gap: 3px;
  padding: 2px 4px;
  border: 1px solid transparent;
  border-radius: 7px;
  background: transparent;
  line-height: 1;
  cursor: pointer;
  transition: all 0.2s ease;
}
.prod-status-btn:hover:not(:disabled) {
  border-color: var(--el-color-primary-light-7, #d9ecff);
  background: var(--adm-blue-bg, #eef4ff);
}
.prod-status-btn:disabled { cursor: default; }

/* 待发布→返工/废弃：与编辑弹窗一致的创意视频卡片 + 双按钮 */
.status-choice-body { display: flex; flex-direction: column; gap: 10px; padding: 4px 0; }
.status-choice-label { font-size: 13px; font-weight: 600; color: var(--adm-text-regular); }
.status-choice-tip { margin: 0; font-size: 12px; line-height: 1.6; color: var(--adm-text-secondary); }

.char-cell { display: flex; align-items: center; gap: 5px; flex-wrap: wrap; }
.char-avatar { width: 48px; height: 48px; border-radius: 10px; border: 1px solid rgba(123, 163, 209, 0.2); display: block; flex-shrink: 0; background: var(--adm-panel-soft); }
.char-avatar.is-empty { opacity: 0.55; }

/* 创作时间：开始 / 完成上下两行，图标区分 */
.prod-time-cell { display: flex; flex-direction: column; gap: 3px; width: 100%; }
.prod-time-row { display: inline-flex; align-items: center; gap: 4px; font-size: 11px; color: var(--adm-text-secondary); }
.prod-time-row.is-start .el-icon { color: #409eff; }
.prod-time-row.is-done .el-icon { color: #3da377; }
.prod-time-row > span:first-of-type { color: var(--adm-text-tertiary); }
.prod-time-row .adm-cell-time { font-size: 11px; }

/* 提示词列：最多两行，溢出省略，不做悬浮提示 */
.prompt-cell {
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  overflow: hidden;
  word-break: break-word;
  line-height: 1.4;
  font-size: 12.5px;
  color: var(--adm-text-secondary);
  white-space: pre-line;
}

/* 制作中确认完成弹窗：参考视频卡片（与编辑弹窗参考视频一致）+ 完成日期选择 */
.complete-body { padding: 4px 0; }
.complete-ref-video {
  display: flex;
  gap: 12px;
  align-items: flex-start;
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  margin-bottom: 16px;
  border: 1px solid var(--adm-border);
  border-radius: 10px;
  background: var(--adm-panel-soft, #f8fafc);
}
.complete-ref-cover {
  width: 72px;
  height: 72px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid var(--adm-border);
  background: var(--adm-panel);
}
.complete-ref-cover.is-empty { opacity: 0.6; }
.complete-ref-info {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 5px;
  min-height: 72px;
  min-width: 0;
  flex: 1;
}
.complete-ref-title {
  flex-shrink: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--adm-text-primary);
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.complete-ref-readonly { display: flex; flex-wrap: wrap; align-items: center; gap: 8px; flex-shrink: 0; }
/* 标签区：单行折叠，超出显示 +N，标题不被挤压 */
.complete-ref-info :deep(.tag-cell-root),
.ref-video-info :deep(.tag-cell-root) { flex-shrink: 0; }
.complete-field label {
  display: block;
  margin-bottom: 6px;
  font-size: 13px;
  font-weight: 600;
  color: var(--adm-text-regular);
}
.complete-tip { margin: 10px 0 0; font-size: 12px; color: var(--adm-text-placeholder); line-height: 1.5; }

/* 视频名称第二行：作者 + 类别（复刻创意灵感） */
.idea-author { color: var(--adm-text-secondary); margin-right: 6px; }
/* 话题标签：最多两行换行显示（与创意灵感一致） */
.idea-tags { max-height: 56px; overflow: hidden; }

/* 编辑弹窗：沿用全局公共弹窗视觉令牌，仅补充表单区布局 */
/* 弹窗限高与 flex 布局见 style.css 的 .edit-dialog.el-dialog 全局规则 */
.edit-dialog-body { padding: 4px 2px; height: 100%; overflow-y: auto; }
.edit-dialog-footer {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
  padding: 12px 4px 4px;
  margin-top: 6px;
  /* 矮屏下吸附在弹窗内容区底部，避免按钮随长表单滚出视口 */
  position: sticky;
  bottom: 0;
  z-index: 2;
  background: var(--adm-surface-solid, #fff);
}
/* 底部按钮统一样式：胶囊、同高、主色系 */
.edit-dialog-footer .el-button {
  min-width: 84px;
  border-radius: 999px;
  font-weight: 600;
}
/* 人物模型：已选资产图片卡片（可删除）+ 选择入口 */
.model-selected-list { display: flex; flex-wrap: wrap; align-items: stretch; gap: 8px; width: 100%; }
.model-selected-item {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 3px;
  width: 72px; padding: 6px 4px; border: 1px solid var(--adm-border); border-radius: 8px;
  background: var(--adm-panel-soft, #f8fafc);
}
.model-selected-cover { width: 56px; height: 56px; border-radius: 6px; object-fit: cover; background: var(--adm-panel); }
.model-selected-name { max-width: 64px; font-size: 11px; line-height: 1.3; color: var(--adm-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.model-remove {
  position: absolute; top: -6px; right: -6px; width: 18px; height: 18px; padding: 0;
  border: none; border-radius: 50%; background: #e28a8a; color: #fff;
  font-size: 14px; line-height: 16px; cursor: pointer;
}
.model-remove:hover { background: #d37272; }
.model-add {
  display: inline-flex; align-items: center; justify-content: center; gap: 4px;
  min-width: 108px; min-height: 76px; padding: 8px 12px;
  border: 1px dashed var(--el-color-primary-light-5, #b3d1ee); border-radius: 8px;
  background: var(--adm-blue-bg, #eef4ff); color: var(--el-color-primary, #4a7cc4);
  font-size: 12px; cursor: pointer;
}
.model-add:hover { background: #e3eeff; }
/* 人物模型选择弹窗：全部人物资产图片卡片 */
.model-picker-grid {
  display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr)); gap: 12px;
  max-height: 52vh; overflow-y: auto; padding: 4px 2px;
}
.model-picker-item {
  position: relative; display: flex; flex-direction: column; align-items: center; gap: 6px;
  padding: 8px 6px; border: 1px solid var(--adm-border); border-radius: 10px;
  background: var(--adm-panel, #fff); color: inherit; cursor: pointer;
}
.model-picker-item:hover { border-color: var(--el-color-primary-light-5, #b3d1ee); background: var(--adm-panel-soft, #f8fafc); }
.model-picker-item.is-selected { border-color: var(--el-color-primary, #4a7cc4); background: var(--adm-blue-bg, #eef4ff); }
.model-picker-cover { width: 96px; height: 96px; border-radius: 8px; object-fit: cover; background: var(--adm-panel-soft, #f8fafc); }
.model-picker-name { max-width: 100%; font-size: 12px; color: var(--adm-text-regular, #303133); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.model-picker-check { position: absolute; top: 4px; right: 6px; color: var(--el-color-primary, #4a7cc4); font-size: 18px; line-height: 1; }
.model-picker-empty { padding: 32px 0; text-align: center; color: var(--adm-text-placeholder, #a8abb2); font-size: 13px; }

/* 只读项：类型 / 制作人 / 状态，横向排列在参考视频卡片内，无小标题 */
.readonly-row { display: flex; flex-wrap: wrap; align-items: center; gap: 12px; }
.readonly-item { display: inline-flex; align-items: center; }
.edit-dialog :deep(.adm-drawer-section) { margin-bottom: 4px; }
.edit-dialog :deep(.el-form-item) { margin-bottom: 14px; }
/* 参考视频：只读展示（封面 + 可点击标题 / 标签），抖音链接不再单独显示 */
.ref-video-view {
  display: flex;
  gap: 14px;
  align-items: flex-start;
  width: 100%;
  box-sizing: border-box;
  padding: 10px 12px;
  border: 1px solid var(--adm-border);
  border-radius: 10px;
  background: var(--adm-panel-soft, #f8fafc);
}
.ref-cover {
  width: 92px;
  height: 92px;
  border-radius: 8px;
  object-fit: cover;
  flex-shrink: 0;
  border: 1px solid var(--adm-border);
  background: var(--adm-panel);
}
.ref-cover.is-empty { opacity: 0.6; }
/* 新建弹窗：封面默认图 + 作者/创作人只读提示 */
/* 右侧三行（标题 / 标签 / 只读项）与左侧 92px 封面等高，垂直方向平分对齐 */
.ref-video-info {
  display: flex;
  flex-direction: column;
  justify-content: flex-start;
  gap: 6px;
  min-height: 92px;
  min-width: 0;
  flex: 1;
}
.ref-title { flex-shrink: 0; font-size: 14px; font-weight: 600; color: var(--adm-text-primary); line-height: 1.4; }
.ref-title-link { text-decoration: none; cursor: pointer; }
.ref-title-link:hover { text-decoration: underline; color: var(--el-color-primary); }
.prompt-textarea { width: 100%; }
</style>
