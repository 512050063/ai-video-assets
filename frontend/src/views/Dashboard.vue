<template>
  <div class="stack dash" v-loading="loading">
    <PageHeader :icon="DataLine" title="首页" desc="一屏掌握视频制作排期与账号发布表现">
      <template #extra>
        <el-select v-model="scope" style="width: 120px" @change="load">
          <el-option value="all" label="全部成员" />
          <el-option value="mine" label="仅我的" />
        </el-select>
      </template>
    </PageHeader>

    <!-- 欢迎条：只保留氛围与今日重点，不抢占数据视线 -->
    <section class="hero">
      <span class="hero-orb hero-orb--one"></span>
      <span class="hero-orb hero-orb--two"></span>
      <div class="hero-inner">
        <div class="hero-copy">
          <div class="hero-eyebrow"><span class="live-dot"></span> 工作台 · {{ weekdayFull }}</div>
          <h2>{{ greeting }}，{{ auth.displayName || '管理员' }}</h2>
          <p>
            今日重点：{{ data.idea_unused || 0 }} 条创意待排期 ·
            {{ data.schedule_pending || 0 }} 条创意待制作 ·
            {{ data.production_making || 0 }} 条视频制作中
          </p>
          <div class="hero-actions">
            <button class="hero-btn hero-btn--primary" @click="router.push('/ideas')">
              查看排期 <el-icon><ArrowRight /></el-icon>
            </button>
            <button class="hero-btn" @click="router.push('/publish-stats')">发布数据</button>
          </div>
        </div>

        <div class="hero-side">
          <div class="hero-ring" :style="{ '--pct': flowRate }">
            <div class="hero-ring-inner">
              <b>{{ flowRate }}%</b>
              <small>发布完成率</small>
            </div>
          </div>
          <div class="hero-meta">
            <div class="hero-meta-line"><el-icon :size="13"><Calendar /></el-icon>{{ fullDate }} {{ dayPeriod }}</div>
            <div class="hero-meta-line">
              <el-icon :size="13"><component :is="weather.icon" /></el-icon>
              <b>{{ weather.temp }}° {{ weather.text }}</b>
            </div>
            <el-select
              v-model="selectedCity"
              class="city-select"
              value-key="id"
              filterable
              remote
              size="small"
              placeholder="搜索城市"
              :remote-method="searchCities"
              :loading="cityLoading"
              @change="onCityChange"
            >
              <el-option :value="CURRENT_LOCATION" label="使用当前位置" />
              <el-option v-for="city in cityOptions" :key="city.id" :value="city" :label="city.full" />
            </el-select>
          </div>
        </div>
      </div>
    </section>

    <!-- 两条主线：制作排期 / 账号发布数据 -->
    <div class="dash-grid">
        <section class="panel panel--schedule">
          <header class="panel-head">
            <div class="panel-title-wrap">
              <span class="panel-icon panel-icon--blue"><el-icon :size="18"><Calendar /></el-icon></span>
              <div>
                <h3>视频制作排期</h3>
                <p>从创意到发布的产能节奏</p>
              </div>
            </div>
            <button class="panel-link" @click="router.push('/ideas')">
              创意排期 <el-icon><ArrowRight /></el-icon>
            </button>
          </header>

          <div class="kpi-grid kpi-grid--4">
            <div v-for="k in scheduleKpis" :key="k.label" class="kpi" :class="`kpi--${k.tone}`">
              <span class="kpi-icon"><el-icon :size="15"><component :is="k.icon" /></el-icon></span>
              <b class="kpi-value">{{ k.value }}</b>
              <span class="kpi-label">{{ k.label }}</span>
            </div>
          </div>

          <div class="section-caption">
            <span>近 14 天 · 排期与发布趋势</span>
            <small>按排期日期 / 发布时间统计</small>
          </div>
          <TrendChart :labels="chartLabels" :series="scheduleSeries" />

          <div class="section-caption section-caption--tight">
            <span>即将到期</span>
            <small>{{ (data.upcoming_ideas || []).length }} 条创意</small>
          </div>
          <div class="upcoming-list">
            <div v-for="row in data.upcoming_ideas || []" :key="row.id" class="upcoming-row">
              <span class="upcoming-date">{{ row.date }}</span>
              <div class="upcoming-main">
                <b :title="row.title">{{ row.title }}</b>
                <small>{{ row.owner }} · {{ row.priority === 1 ? '高优先级' : row.priority === 3 ? '低优先级' : '中优先级' }}</small>
              </div>
              <span class="status-pill" :class="row.status === '制作中' ? 'is-making' : 'is-pending'">{{ row.status }}</span>
            </div>
            <div v-if="!(data.upcoming_ideas || []).length" class="list-empty">暂无已排期创意，排期节奏很稳</div>
          </div>
        </section>

        <section class="panel panel--publish">
          <header class="panel-head">
            <div class="panel-title-wrap">
              <span class="panel-icon panel-icon--mint"><el-icon :size="18"><TrendCharts /></el-icon></span>
              <div>
                <h3>账号发布数据</h3>
                <p>发布表现与账号贡献一目了然</p>
              </div>
            </div>
            <button class="panel-link" @click="router.push('/publish-stats')">
              数据中心 <el-icon><ArrowRight /></el-icon>
            </button>
          </header>

          <div class="kpi-grid kpi-grid--3">
            <div v-for="k in publishKpis" :key="k.label" class="kpi" :class="`kpi--${k.tone}`">
              <b class="kpi-value">{{ k.value }}</b>
              <span class="kpi-label">{{ k.label }}</span>
            </div>
          </div>

          <div class="section-caption">
            <span>近 14 天 · 播放趋势</span>
            <small>按数据快照日期统计</small>
          </div>
          <TrendChart :labels="chartLabels" :series="publishSeries" />

          <div class="section-caption section-caption--tight">
            <span>账号表现 TOP</span>
            <small>按累计播放排序</small>
          </div>
          <div class="rank-list">
            <div v-for="(row, i) in data.account_ranking || []" :key="row.name" class="rank-row">
              <span class="rank-no" :class="{ 'is-top': i === 0 }">{{ i + 1 }}</span>
              <span class="rank-avatar">
                <img v-if="row.avatar" :src="row.avatar" :alt="row.name" />
                <el-icon v-else><User /></el-icon>
              </span>
              <div class="rank-main">
                <div class="rank-line">
                  <b :title="row.name">{{ row.name }}</b>
                  <span class="rank-plays">{{ formatNumber(row.plays) }}</span>
                </div>
                <div class="rank-bar"><i :style="{ width: `${rankWidth(row.plays)}%` }"></i></div>
              </div>
            </div>
            <div v-if="!(data.account_ranking || []).length" class="list-empty">暂无发布数据，去数据中心录入或采集</div>
          </div>

          <div class="engagement">
            <div><small>累计评论</small><b>{{ formatNumber(data.comments_total || 0) }}</b></div>
            <div><small>累计转发</small><b>{{ formatNumber(data.shares_total || 0) }}</b></div>
            <div><small>数据快照</small><b>{{ snapshotCount }}</b></div>
          </div>
        </section>
    </div>

    <!-- 账号更新提醒：属于发布数据的一条可执行动作 -->
    <section v-if="dueReminders.length" class="reminder-strip" v-loading="reminderLoading">
      <div class="reminder-head">
        <span class="reminder-title"><el-icon :size="14"><Lightning /></el-icon> {{ dueReminders.length }} 个账号待更新</span>
        <button class="panel-link" @click="router.push('/publish-accounts')">管理账号 <el-icon><ArrowRight /></el-icon></button>
      </div>
      <div class="reminder-track">
        <div v-for="item in dueReminders.slice(0, 8)" :key="item.account_id" class="reminder-card">
          <img v-if="item.avatar" :src="item.avatar" :alt="item.account_name" />
          <span v-else class="reminder-avatar-empty"><el-icon><User /></el-icon></span>
          <div class="reminder-copy">
            <b :title="item.account_name">{{ item.account_name }}</b>
            <small>{{ item.update_rhythm || '日更' }} · {{ item.reason }}</small>
          </div>
          <el-button
            type="primary"
            size="small"
            class="reminder-btn"
            :loading="schedulingId === item.account_id"
            @click="scheduleAccount(item)"
          >排期</el-button>
        </div>
      </div>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import {
  ArrowRight,
  Calendar,
  Cloudy,
  Collection,
  DataLine,
  Lightning,
  List,
  MoonNight,
  PartlyCloudy,
  MostlyCloudy,
  Star,
  Sunrise,
  Sunset,
  Sunny,
  TrendCharts,
  User,
  VideoCamera,
  VideoPlay
} from '@element-plus/icons-vue'
import PageHeader from '../components/PageHeader.vue'
import TrendChart from '../components/ui/TrendChart.vue'
import { api } from '../api'
import { useAuthStore } from '../stores/auth'
import { usePermissionStore } from '../stores/permission'
import { useSettingsStore } from '../stores/settings'

const auth = useAuthStore()
const perm = usePermissionStore()
const settings = useSettingsStore()
const router = useRouter()

const loading = ref(false)
const data = ref({})
const scope = ref('all')
const now = ref(new Date())
let clockTimer = null

const reminderLoading = ref(false)
const dueReminders = ref([])
const schedulingId = ref(null)

const WEEK_FULL = ['星期日', '星期一', '星期二', '星期三', '星期四', '星期五', '星期六']
const CURRENT_LOCATION = { id: '__current__', name: '当前位置', full: '使用当前位置', current: true }

const WEATHER_SYMBOLS = {
  clearsky: ['晴', Sunny],
  fair: ['晴间多云', PartlyCloudy],
  partlycloudy: ['多云', PartlyCloudy],
  cloudy: ['阴', Cloudy],
  fog: ['雾', Cloudy],
  rain: ['小雨', Cloudy],
  lightrain: ['小雨', Cloudy],
  heavyrain: ['大雨', Cloudy],
  sleet: ['雨夹雪', MostlyCloudy],
  snow: ['雪', MostlyCloudy],
  thunderstorm: ['雷阵雨', Lightning]
}

const weather = ref({ temp: '--', text: '天气获取中', icon: Cloudy })
const cityOptions = ref([])
const cityLoading = ref(false)
const selectedCity = ref({ id: 'default', name: '深圳', full: '深圳', lat: null, lon: null })

const greeting = computed(() => {
  const h = now.value.getHours()
  if (h < 6 || h >= 22) return '夜深了'
  if (h < 11) return '早上好'
  if (h < 14) return '中午好'
  if (h < 18) return '下午好'
  return '晚上好'
})
const dayPeriod = computed(() => {
  const h = now.value.getHours()
  if (h < 6) return '凌晨'
  if (h < 11) return '上午'
  if (h < 14) return '中午'
  if (h < 18) return '下午'
  return '晚上'
})
const fullDate = computed(() => {
  const d = now.value
  return `${d.getFullYear()}年${d.getMonth() + 1}月${d.getDate()}日`
})
const weekdayFull = computed(() => WEEK_FULL[now.value.getDay()])

const flowRate = computed(() => {
  const total = data.value.production_total || 0
  return total ? Math.round(((data.value.production_published || 0) / total) * 100) : 0
})

const scheduleKpis = computed(() => [
  { label: '待排期创意', value: data.value.idea_unused || 0, tone: 'amber', icon: Collection },
  { label: '待制作创意', value: data.value.schedule_pending || 0, tone: 'blue', icon: List },
  { label: '制作中', value: data.value.production_making || 0, tone: 'violet', icon: VideoCamera },
  { label: '已发布', value: data.value.production_published || 0, tone: 'green', icon: VideoPlay }
])
const publishKpis = computed(() => [
  { label: '累计播放', value: data.value.plays_total || 0, tone: 'blue' },
  { label: '累计点赞', value: data.value.likes_total || 0, tone: 'amber' },
  { label: '本月发布', value: data.value.published_this_month || 0, tone: 'green' }
])

const chartLabels = computed(() => (data.value.schedule_trend || []).map((x) => x.date))
const scheduleSeries = computed(() => [
  { name: '排期', color: '#5b8ff9', values: (data.value.schedule_trend || []).map((x) => x.planned) },
  { name: '发布', color: '#37b98a', values: (data.value.schedule_trend || []).map((x) => x.published) }
])
const publishSeries = computed(() => [
  { name: '播放量', color: '#5b8ff9', values: (data.value.publish_trend || []).map((x) => x.plays) },
  { name: '点赞', color: '#f5a65b', values: (data.value.publish_trend || []).map((x) => x.likes) }
])
const maxRankPlays = computed(() => Math.max(1, ...(data.value.account_ranking || []).map((x) => x.plays || 0)))
const snapshotCount = computed(() => (data.value.publish_trend || []).reduce((sum, x) => sum + (x.count || 0), 0))

function formatNumber(v) {
  const n = Number(v) || 0
  if (n >= 10000) return `${(n / 10000).toFixed(1)}万`
  if (n >= 1000) return `${(n / 1000).toFixed(1)}k`
  return String(n)
}
function rankWidth(v) {
  return Math.max(4, Math.round(((Number(v) || 0) / maxRankPlays.value) * 100))
}
function toNum(value) {
  const n = Number(value)
  return Number.isFinite(n) ? Math.round(n) : '--'
}
function makeCityOption(item) {
  const lat = Number(item.latitude)
  const lon = Number(item.longitude)
  return {
    id: String(item.id ?? `${lat},${lon}`),
    name: item.name,
    full: [item.country, item.admin1, item.name].filter(Boolean).join(' · '),
    lat,
    lon
  }
}
function hasCoords(place) {
  if (!place) return false
  const lat = Number(place.lat)
  const lon = Number(place.lon)
  return Number.isFinite(lat) && Number.isFinite(lon) && !(lat === 0 && lon === 0)
}

async function searchCities(query) {
  const kw = String(query || '').trim()
  if (!kw) {
    cityOptions.value = selectedCity.value ? [selectedCity.value] : []
    return
  }
  cityLoading.value = true
  try {
    const params = new URLSearchParams({ name: kw, count: '8', language: 'zh', format: 'json' })
    const res = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`)
    if (!res.ok) throw new Error('geocoding failed')
    const geo = await res.json()
    const options = (geo.results || []).map(makeCityOption)
    if (selectedCity.value && !options.some((c) => c.id === selectedCity.value.id)) options.unshift(selectedCity.value)
    cityOptions.value = options
  } catch {
    cityOptions.value = selectedCity.value ? [selectedCity.value] : []
  } finally {
    cityLoading.value = false
  }
}

async function persistCity(place) {
  if (!perm.can('settings.manage')) {
    ElMessage.info('已切换当前天气城市；无「修改配置」权限，仅当前会话生效')
    return
  }
  try {
    await settings.save('welcome', {
      city: place.name,
      latitude: hasCoords(place) ? Number(place.lat) : null,
      longitude: hasCoords(place) ? Number(place.lon) : null
    })
  } catch {
    ElMessage.warning('已切换当前天气城市，但默认位置保存失败')
  }
}

function useCurrentLocation() {
  if (!navigator.geolocation) {
    ElMessage.warning('当前浏览器不支持定位')
    return
  }
  cityLoading.value = true
  navigator.geolocation.getCurrentPosition(
    async ({ coords }) => {
      const place = { id: CURRENT_LOCATION.id, name: CURRENT_LOCATION.name, full: CURRENT_LOCATION.full, current: true, lat: coords.latitude, lon: coords.longitude }
      selectedCity.value = place
      cityOptions.value = [place, ...cityOptions.value.filter((c) => c.id !== place.id)]
      cityLoading.value = false
      await persistCity(place)
      loadWeather(place)
    },
    () => {
      cityLoading.value = false
      ElMessage.warning('定位失败，请检查浏览器定位权限')
    },
    { enableHighAccuracy: false, timeout: 10000, maximumAge: 60000 }
  )
}

async function onCityChange(place) {
  if (!place) return
  if (place.current) return useCurrentLocation()
  await persistCity(place)
  loadWeather(place)
}

async function loadWeather(placeRef = null) {
  const configured = settings.welcome || {}
  const city = String(placeRef?.name || configured.city || '').trim() || '深圳'
  weather.value = { ...weather.value, text: '天气获取中' }
  try {
    let place = placeRef
    if (!hasCoords(place) && !placeRef && hasCoords(configured)) {
      place = { name: city, full: city, lat: configured.latitude, lon: configured.longitude }
    }
    if (!hasCoords(place)) {
      const params = new URLSearchParams({ name: city, count: '1', language: 'zh', format: 'json' })
      const geoRes = await fetch(`https://geocoding-api.open-meteo.com/v1/search?${params}`)
      if (!geoRes.ok) throw new Error('geocoding failed')
      const found = (await geoRes.json()).results?.[0]
      if (!found) throw new Error('city not found')
      place = makeCityOption(found)
    }
    const query = new URLSearchParams({ lat: place.lat, lon: place.lon })
    const res = await fetch(`https://api.met.no/weatherapi/locationforecast/2.0/compact?${query}`)
    if (!res.ok) throw new Error('weather failed')
    const w = await res.json()
    const current = w.properties?.timeseries?.[0]?.data || {}
    const details = current.instant?.details || {}
    const symbol = String(current.next_1_hours?.summary?.symbol_code || '').replace(/_(day|night)$/, '')
    const [text, icon] = WEATHER_SYMBOLS[symbol] || ['天气多变', Cloudy]
    weather.value = { temp: toNum(details.air_temperature), text, icon }
  } catch {
    weather.value = { temp: '--', text: '天气暂不可用', icon: Cloudy }
  }
}

async function load() {
  loading.value = true
  try {
    const { data: d } = await api.get('/dashboard', { params: { scope: scope.value } })
    data.value = d
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败，请重试')
  } finally {
    loading.value = false
  }
}

async function loadReminders() {
  reminderLoading.value = true
  try {
    const { data } = await api.get('/publish-accounts/reminders', { params: { only_due: 1, scope: scope.value } })
    dueReminders.value = Array.isArray(data) ? data : []
  } catch {
    dueReminders.value = []
  } finally {
    reminderLoading.value = false
  }
}

async function scheduleAccount(item) {
  schedulingId.value = item.account_id
  try {
    const { data } = await api.post(`/publish-accounts/${item.account_id}/schedule`)
    ElMessage.success(`已生成创意「${data.title || ''}」`)
    await loadReminders()
    router.push({ path: '/ideas' })
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '排期失败，请重试')
  } finally {
    schedulingId.value = null
  }
}

onMounted(async () => {
  await settings.load()
  const configured = settings.welcome || {}
  const cityName = String(configured.city || '').trim() || '深圳'
  const savedCoord = hasCoords(configured)
  selectedCity.value = savedCoord
    ? { id: 'saved', name: cityName, full: cityName, lat: Number(configured.latitude), lon: Number(configured.longitude) }
    : { id: 'default', name: cityName, full: cityName, lat: null, lon: null }
  cityOptions.value = [selectedCity.value]
  loadWeather()
  load()
  loadReminders()
  clockTimer = setInterval(() => { now.value = new Date() }, 60 * 1000)
})

onUnmounted(() => {
  if (clockTimer) clearInterval(clockTimer)
})
</script>

<style scoped>
.dash {
  gap: 16px;
}

/* ---------- 欢迎条 ---------- */
.hero {
  position: relative;
  overflow: hidden;
  border-radius: 20px;
  padding: 24px 28px;
  color: #fff;
  background: linear-gradient(115deg, #4358b6 0%, #5a6fd8 48%, #6d8ae4 100%);
  box-shadow: 0 14px 34px rgba(67, 88, 182, 0.18);
}
.hero-orb {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.14);
  filter: blur(2px);
  pointer-events: none;
  animation: orb-float 9s ease-in-out infinite alternate;
}
.hero-orb--one { width: 220px; height: 220px; right: 18%; top: -120px; }
.hero-orb--two { width: 160px; height: 160px; right: -40px; bottom: -90px; animation-delay: -4s; }
@keyframes orb-float {
  from { transform: translate3d(0, 0, 0) scale(1); }
  to { transform: translate3d(-24px, 18px, 0) scale(1.12); }
}
.hero-inner {
  position: relative;
  z-index: 1;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 24px;
}
.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 7px;
  font-size: 12px;
  letter-spacing: 0.4px;
  opacity: 0.82;
}
.live-dot {
  width: 7px; height: 7px; border-radius: 50%;
  background: #9df5c4;
  box-shadow: 0 0 0 4px rgba(157, 245, 196, 0.18);
  animation: dot-pulse 2.4s ease-in-out infinite;
}
@keyframes dot-pulse {
  50% { box-shadow: 0 0 0 8px rgba(157, 245, 196, 0); }
}
.hero-copy h2 {
  margin: 10px 0 6px;
  font-size: 25px;
  line-height: 1.2;
  font-weight: 700;
}
.hero-copy p {
  margin: 0;
  font-size: 12.5px;
  opacity: 0.86;
}
.hero-actions {
  display: flex;
  gap: 10px;
  margin-top: 16px;
}
.hero-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 15px;
  border: 1px solid rgba(255, 255, 255, 0.45);
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.12);
  color: #fff;
  font-size: 12.5px;
  cursor: pointer;
  transition: transform 0.18s ease, background 0.18s ease;
}
.hero-btn:hover { transform: translateY(-2px); background: rgba(255, 255, 255, 0.22); }
.hero-btn--primary { background: #fff; color: #4b5fc0; border-color: #fff; font-weight: 600; }
.hero-side { display: flex; align-items: center; gap: 22px; }
.hero-ring {
  width: 92px; height: 92px; flex-shrink: 0;
  border-radius: 50%;
  background: conic-gradient(#a7f3d0 calc(var(--pct) * 1%), rgba(255, 255, 255, 0.2) 0);
  display: grid; place-items: center;
  animation: ring-in 1.1s cubic-bezier(0.2, 0.8, 0.3, 1) both;
}
@keyframes ring-in { from { transform: scale(0.7); opacity: 0; } }
.hero-ring-inner {
  width: 74px; height: 74px; border-radius: 50%;
  background: #5569cf;
  display: flex; flex-direction: column; align-items: center; justify-content: center;
}
.hero-ring-inner b { font-size: 21px; line-height: 1.1; }
.hero-ring-inner small { font-size: 10px; opacity: 0.78; margin-top: 2px; }
.hero-meta { display: flex; flex-direction: column; gap: 7px; min-width: 132px; }
.hero-meta-line { display: flex; align-items: center; gap: 7px; font-size: 12px; opacity: 0.9; }
.city-select { width: 132px; }
.city-select :deep(.el-select__wrapper) {
  min-height: 24px; padding: 0 8px; border-radius: 8px;
  background: rgba(255, 255, 255, 0.14); box-shadow: none !important;
}
.city-select :deep(.el-select__selected-item) { color: #fff; font-size: 11.5px; }
.city-select :deep(.el-select__placeholder) { color: rgba(255, 255, 255, 0.7); font-size: 11.5px; }
.city-select :deep(.el-select__caret) { color: #fff; }

/* ---------- 两块主面板 ---------- */
.dash-grid {
  display: grid;
  grid-template-columns: minmax(0, 14fr) minmax(0, 10fr);
  gap: 16px;
  align-items: stretch;
}
.panel {
  min-width: 0;
  min-width: 0;
  padding: 20px;
  border-radius: 18px;
  border: 1px solid var(--adm-border);
  background: var(--adm-card-bg, #fff);
  box-shadow: 0 4px 18px rgba(31, 45, 80, 0.04);
  animation: panel-in 0.55s ease both;
}
.panel--schedule { animation-delay: 0.05s; }
.panel--publish { animation-delay: 0.15s; display: flex; flex-direction: column; }
@keyframes panel-in { from { transform: translateY(12px); opacity: 0; } }
.panel-head {
  display: flex; align-items: center; justify-content: space-between; gap: 12px;
  padding-bottom: 16px; border-bottom: 1px solid var(--adm-border);
}
.panel-title-wrap { display: flex; align-items: center; gap: 12px; min-width: 0; }
.panel-title-wrap h3 { margin: 0; font-size: 16px; color: var(--adm-text-primary); font-weight: 700; }
.panel-title-wrap p { margin: 3px 0 0; font-size: 11.5px; color: var(--adm-text-secondary); }
.panel-icon {
  width: 38px; height: 38px; flex-shrink: 0;
  border-radius: 12px; display: grid; place-items: center;
}
.panel-icon--blue { color: #4d7fe6; background: rgba(77, 127, 230, 0.12); }
.panel-icon--mint { color: #23a679; background: rgba(35, 166, 121, 0.12); }
.panel-link {
  display: inline-flex; align-items: center; gap: 4px;
  border: 0; background: transparent; color: var(--el-color-primary);
  font-size: 12px; cursor: pointer; white-space: nowrap;
}
.panel-link:hover { text-decoration: underline; }

.kpi-grid { display: grid; gap: 10px; margin: 16px 0 18px; }
.kpi-grid--4 { grid-template-columns: repeat(4, minmax(0, 1fr)); }
.kpi-grid--3 { grid-template-columns: repeat(3, minmax(0, 1fr)); }
.kpi {
  position: relative; overflow: hidden;
  min-width: 0; padding: 12px 13px;
  border-radius: 13px;
  border: 1px solid var(--adm-border);
  background: var(--adm-panel);
  display: flex; flex-direction: column; gap: 3px;
  transition: transform 0.2s ease, box-shadow 0.2s ease;
  animation: kpi-in 0.5s ease both;
}
.kpi:hover { transform: translateY(-3px); box-shadow: 0 8px 18px rgba(31, 45, 80, 0.08); }
.kpi:nth-child(2) { animation-delay: 0.06s; }
.kpi:nth-child(3) { animation-delay: 0.12s; }
.kpi:nth-child(4) { animation-delay: 0.18s; }
@keyframes kpi-in { from { transform: translateY(8px); opacity: 0; } }
.kpi-icon {
  width: 24px; height: 24px; border-radius: 8px;
  display: grid; place-items: center; margin-bottom: 3px;
}
.kpi-value { font-size: 22px; line-height: 1.15; font-weight: 750; color: var(--adm-text-primary); }
.kpi-label { font-size: 11.5px; color: var(--adm-text-secondary); white-space: nowrap; }
.kpi--amber .kpi-icon { color: #d98a28; background: rgba(230, 162, 60, 0.14); }
.kpi--amber .kpi-value { color: #c77b1d; }
.kpi--blue .kpi-icon { color: #4d7fe6; background: rgba(77, 127, 230, 0.13); }
.kpi--blue .kpi-value { color: #3f70dc; }
.kpi--violet .kpi-icon { color: #8065d9; background: rgba(128, 101, 217, 0.13); }
.kpi--violet .kpi-value { color: #7357cf; }
.kpi--green .kpi-icon { color: #23a679; background: rgba(35, 166, 121, 0.13); }
.kpi--green .kpi-value { color: #19976c; }

.section-caption {
  display: flex; align-items: baseline; justify-content: space-between; gap: 10px;
  margin: 4px 0 10px;
}
.section-caption--tight { margin-top: 20px; padding-top: 16px; border-top: 1px dashed var(--adm-border); }
.section-caption span { font-size: 13px; font-weight: 650; color: var(--adm-text-primary); }
.section-caption small { font-size: 11px; color: var(--adm-text-placeholder); }

.upcoming-list, .rank-list { display: flex; flex-direction: column; gap: 7px; }
.upcoming-row {
  display: flex; align-items: center; gap: 11px;
  padding: 9px 11px; border-radius: 11px;
  background: var(--adm-panel); border: 1px solid var(--adm-border);
  transition: background 0.18s ease, transform 0.18s ease;
}
.upcoming-row:hover { background: var(--adm-panel-hover); transform: translateX(2px); }
.upcoming-date {
  flex-shrink: 0; width: 44px; text-align: center;
  font-size: 11.5px; font-weight: 700; color: var(--el-color-primary);
}
.upcoming-main { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.upcoming-main b { font-size: 12.5px; color: var(--adm-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.upcoming-main small { font-size: 11px; color: var(--adm-text-secondary); }
.status-pill {
  flex-shrink: 0; font-size: 11px; padding: 3px 9px; border-radius: 999px;
}
.status-pill.is-pending { color: #b57a20; background: rgba(230, 162, 60, 0.13); }
.status-pill.is-making { color: #4d7fe6; background: rgba(77, 127, 230, 0.13); }

.rank-row { display: flex; align-items: center; gap: 10px; padding: 7px 9px; border-radius: 11px; transition: background 0.18s ease; }
.rank-row:hover { background: var(--adm-panel); }
.rank-no {
  flex-shrink: 0; width: 20px; height: 20px; border-radius: 7px;
  display: grid; place-items: center; font-size: 11px; font-weight: 700;
  color: var(--adm-text-secondary); background: var(--adm-panel);
}
.rank-no.is-top { color: #fff; background: linear-gradient(135deg, #f6b34b, #ef8f3a); }
.rank-avatar {
  flex-shrink: 0; width: 30px; height: 30px; border-radius: 9px; overflow: hidden;
  display: grid; place-items: center; color: var(--adm-text-placeholder); background: var(--adm-panel);
}
.rank-avatar img { width: 100%; height: 100%; object-fit: cover; }
.rank-main { flex: 1; min-width: 0; }
.rank-line { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
.rank-line b { font-size: 12.5px; color: var(--adm-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.rank-plays { font-size: 11.5px; font-weight: 700; color: var(--el-color-primary); flex-shrink: 0; }
.rank-bar { height: 5px; margin-top: 6px; border-radius: 999px; background: var(--adm-panel); overflow: hidden; }
.rank-bar i {
  display: block; height: 100%; border-radius: 999px;
  background: linear-gradient(90deg, #6fa4f5, #4d7fe6);
  animation: bar-grow 0.9s cubic-bezier(0.22, 0.75, 0.3, 1) both;
  transform-origin: left;
}
@keyframes bar-grow { from { transform: scaleX(0); } }
.list-empty { padding: 18px 0; text-align: center; font-size: 12px; color: var(--adm-text-placeholder); }
.engagement {
  margin-top: auto;
  padding-top: 18px;
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 8px;
}
.engagement > div {
  padding: 10px 8px;
  border-radius: 11px;
  background: var(--adm-panel);
  border: 1px dashed var(--adm-border-deep);
  text-align: center;
  display: flex;
  flex-direction: column;
  gap: 3px;
}
.engagement small { font-size: 10.5px; color: var(--adm-text-secondary); }
.engagement b { font-size: 15px; color: var(--adm-text-primary); }

/* ---------- 更新提醒 ---------- */
.reminder-strip {
  padding: 14px 18px 16px;
  border-radius: 16px;
  border: 1px solid rgba(230, 162, 60, 0.28);
  background: var(--adm-state-warning-bg);
}
.reminder-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 10px; }
.reminder-title { display: inline-flex; align-items: center; gap: 6px; font-size: 12.5px; font-weight: 650; color: #b57a20; }
.reminder-track { display: flex; gap: 10px; overflow-x: auto; padding-bottom: 4px; }
.reminder-card {
  flex: 0 0 240px; display: flex; align-items: center; gap: 9px;
  padding: 9px 11px; border-radius: 12px;
  background: var(--adm-card-bg, #fff); border: 1px solid var(--adm-border);
}
.reminder-card img, .reminder-avatar-empty {
  flex-shrink: 0; width: 32px; height: 32px; border-radius: 9px; object-fit: cover;
  display: grid; place-items: center; color: var(--adm-text-placeholder); background: var(--adm-panel);
}
.reminder-copy { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.reminder-copy b { font-size: 12px; color: var(--adm-text-primary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.reminder-copy small { font-size: 10.5px; color: var(--adm-text-secondary); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.reminder-btn { flex-shrink: 0; height: 26px; padding: 0 10px; font-size: 11.5px; }

@media (max-width: 1200px) {
  .dash-grid { grid-template-columns: minmax(0, 1fr); }
  .kpi-grid--4 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
  .hero-side { gap: 14px; }
}
@media (max-width: 768px) {
  .hero { padding: 20px; }
  .hero-inner { flex-direction: column; align-items: flex-start; }
  .hero-copy h2 { font-size: 21px; }
  .hero-side { width: 100%; justify-content: space-between; }
  .kpi-grid--3 { grid-template-columns: repeat(2, minmax(0, 1fr)); }
}
</style>
