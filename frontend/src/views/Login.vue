<template>
  <!-- 统一背景：整个页面一个渐变底 -->
  <div class="login-page min-h-screen relative overflow-hidden bg-gradient-to-br from-[#f8fafc] via-blue-50/60 to-indigo-100/50">
    <div class="login-aurora login-aurora-a"></div>
    <div class="login-aurora login-aurora-b"></div>
    <div class="login-aurora login-aurora-c"></div>
    <div class="login-spotlight"></div>
    <div class="login-flow-line login-flow-line-a"></div>
    <div class="login-flow-line login-flow-line-b"></div>
    <div class="login-drift-grid"></div>
    <div class="login-glyph login-glyph-a">▶</div>
    <div class="login-glyph login-glyph-b">✦</div>
    <div class="login-glyph login-glyph-c">✂</div>

    <!-- 背景装饰：悬浮素材卡片 -->
    <div class="deco-layer" aria-hidden="true">
      <div class="deco-card deco-1">
        <div class="deco-thumb t-blue"></div>
        <div class="deco-line w-3/5"></div>
        <div class="deco-line w-2/5 short"></div>
      </div>
      <div class="deco-card deco-2">
        <div class="deco-thumb t-indigo"></div>
        <div class="deco-line w-2/3"></div>
        <div class="deco-line w-1/2 short"></div>
      </div>
      <div class="deco-card deco-3">
        <div class="deco-thumb t-amber"></div>
        <div class="deco-line w-1/2"></div>
        <div class="deco-line w-1/3 short"></div>
      </div>
      <div class="deco-card deco-4">
        <div class="deco-thumb t-emerald"></div>
        <div class="deco-line w-3/5"></div>
        <div class="deco-line w-1/3 short"></div>
      </div>
    </div>

    <!-- 主内容区 -->
    <div class="relative z-10 min-h-screen flex justify-center">
      <div class="w-full max-w-[1240px] mx-auto px-6 flex items-stretch justify-between gap-10">
        <!-- 左：品牌区 -->
        <div class="hidden lg:flex w-[600px] py-14 flex-col justify-center login-brand-pane">
          <div class="w-full max-w-[620px] ml-2">
            <!-- Logo + 标题 -->
            <div class="flex items-center mb-6 login-brand-title">
              <div class="login-logo flex items-center justify-center flex-shrink-0">
                <div class="loader_cube loader_cube--color"></div>
                <div class="loader_cube loader_cube--glowing"></div>
                <svg class="w-11 h-11 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <div class="login-brand-text">
                <h1 class="login-brand-name font-bold tracking-tight" style="color: #1e293b">AI 视频创作管理台</h1>
                <div class="text-[13px] text-[#94a3b8] tracking-wide mt-1.5">Creation Console · 本地部署</div>
              </div>
            </div>

            <p class="text-xl text-[#475569] leading-relaxed mb-7 login-brand-subtitle">
              <span>从创意到发布</span>
              <span class="login-marquee-vertical" aria-hidden="true">
                <span class="login-marquee-stack">
                  <span>一站式管理</span>
                  <span>全流程可追踪</span>
                  <span>数据自动更新</span>
                  <span>一站式管理</span>
                </span>
              </span>
            </p>

            <!-- 功能特性列表 -->
            <div class="space-y-5 text-left">
              <div class="login-feature flex items-center cursor-default">
                <div class="login-feature-icon w-12 h-12 rounded-xl bg-blue-50 flex items-center justify-center flex-shrink-0">
                  <svg class="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4" />
                  </svg>
                </div>
                <div class="ml-4 text-left">
                  <h3 class="text-[17px] font-semibold text-[#334155]">创作流程一站打通</h3>
                  <p class="text-[13.5px] text-[#64748b] leading-relaxed mt-0.5">创意灵感、视频创作、发布数据逐级流转，进度与状态全程可查</p>
                </div>
              </div>
              <div class="login-feature flex items-center cursor-default">
                <div class="login-feature-icon w-12 h-12 rounded-xl bg-indigo-50 flex items-center justify-center flex-shrink-0">
                  <svg class="w-6 h-6 text-indigo-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                  </svg>
                </div>
                <div class="ml-4 text-left">
                  <h3 class="text-[17px] font-semibold text-[#334155]">账号数据自动更新</h3>
                  <p class="text-[13.5px] text-[#64748b] leading-relaxed mt-0.5">扫码登录抖音账号，定时采集作品与粉丝数据，历史快照随时对照</p>
                </div>
              </div>
              <div class="login-feature flex items-center cursor-default">
                <div class="login-feature-icon w-12 h-12 rounded-xl bg-amber-50 flex items-center justify-center flex-shrink-0">
                  <svg class="w-6 h-6 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                      d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4" />
                  </svg>
                </div>
                <div class="ml-4 text-left">
                  <h3 class="text-[17px] font-semibold text-[#334155]">资产与权限统一沉淀</h3>
                  <p class="text-[13.5px] text-[#64748b] leading-relaxed mt-0.5">人物资产、素材分库复用，角色权限与配置中心集中管控</p>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- 右：登录卡 -->
        <div class="w-full lg:w-[430px] flex items-center justify-center py-14 relative">
          <div class="w-full max-w-[430px] relative z-10 login-card-panel">
            <div class="lg:hidden flex items-center mb-8">
              <div class="w-10 h-10 bg-gradient-to-br from-blue-600 to-indigo-600 rounded-xl flex items-center justify-center shadow-lg shadow-blue-500/30">
                <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2"
                    d="M15 10l4.553-2.276A1 1 0 0121 8.618v6.764a1 1 0 01-1.447.894L15 14M5 18h8a2 2 0 002-2V8a2 2 0 00-2-2H5a2 2 0 00-2 2v8a2 2 0 002 2z" />
                </svg>
              </div>
              <span class="ml-3 text-xl font-bold text-[#1e293b]">AI 视频创作管理台</span>
            </div>

            <div class="login-card-wrap">
              <div class="login-card rounded-3xl p-9 relative">
              <div class="card-accent"></div>
              <div class="mb-7 text-center login-card-heading">
                <h1 class="text-[26px] font-bold text-[#1e293b] mb-2">{{ isRegister ? '创建账户' : '欢迎回来' }}</h1>
                <p class="text-[#64748b] text-[13.5px]">{{ isRegister ? '填写信息注册新账号' : '请登录您的账户继续使用' }}</p>
              </div>

              <el-form ref="formRef" :model="form" :rules="rules" @submit.prevent class="login-panel-swap">
                <el-form-item prop="username">
                  <el-input v-model="form.username" placeholder="请输入用户名" size="large" clearable>
                    <template #prefix><el-icon><User /></el-icon></template>
                  </el-input>
                </el-form-item>
                <el-form-item v-if="isRegister" prop="nickname">
                  <el-input v-model="form.nickname" placeholder="昵称，可留空" size="large" clearable>
                    <template #prefix><el-icon><Postcard /></el-icon></template>
                  </el-input>
                </el-form-item>
                <el-form-item prop="password">
                  <el-input
                    v-model="form.password"
                    type="password"
                    size="large"
                    show-password
                    placeholder="请输入密码（至少6位）"
                    autocomplete="current-password"
                    @keyup.enter="submit"
                  >
                    <template #prefix><el-icon><Lock /></el-icon></template>
                  </el-input>
                </el-form-item>
                <el-form-item v-if="isRegister" prop="confirm">
                  <el-input v-model="form.confirm" type="password" size="large" show-password placeholder="请再次输入密码" @keyup.enter="submit">
                    <template #prefix><el-icon><Lock /></el-icon></template>
                  </el-input>
                </el-form-item>

                <div v-if="!isRegister" class="login-form-row">
                  <el-checkbox v-model="remember">记住密码</el-checkbox>
                  <span class="login-forget-link" role="button" @click="forgotVisible = true">忘记密码？</span>
                </div>

                <el-form-item>
                  <el-button type="primary" size="large" class="w-full" :loading="loading" native-type="button" @click="submit">
                    {{ loading ? (isRegister ? '注册中...' : '登录中...') : (isRegister ? '注册' : '登录') }}
                  </el-button>
                </el-form-item>
              </el-form>

              <div class="login-register-row">
                <span class="text-sm text-[#64748b]">{{ isRegister ? '已有账户？' : '还没有账号' }}</span>
                <el-button type="primary" link class="login-inline-link text-sm" @click="toggle">
                  {{ isRegister ? '立即登录' : '立即注册' }}
                </el-button>
              </div>

              </div>
            </div>

            <div class="login-foot-note">© 2026 AI 视频创作管理台 · 数据不出本机</div>
          </div>
        </div>
      </div>
    </div>

    <!-- 忘记密码 -->
    <el-dialog v-model="forgotVisible" width="440px" align-center class="login-forgot-dialog">
      <template #header>
        <DialogHeader :icon="QuestionFilled" title="忘记密码" sub="本地部署环境下账号仅存于本机数据库" tone="amber" />
      </template>
      <div class="forgot-body">
        <p>本系统为<b>本地部署</b>，账号与密码保存在本机数据库中，不经过邮箱或短信，因此无法自助找回。</p>
        <p>重置方式任选其一：</p>
        <ol class="forgot-steps">
          <li>联系系统管理员，登录后由管理员在「用户管理」中重置密码；</li>
          <li>直接操作服务端数据库 <code>backend/ai_video_assets.db</code> 的 <code>users</code> 表，重置 <code>password_hash</code> 字段。</li>
        </ol>
      </div>
      <template #footer>
        <el-button type="primary" @click="forgotVisible = false">知道了</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Lock, Postcard, QuestionFilled, User } from '@element-plus/icons-vue'
import DialogHeader from '../components/ui/DialogHeader.vue'
import { useAuthStore } from '../stores/auth'
import { readCreds, writeCreds } from '../utils/session'
const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const isRegister = ref(false)
const loading = ref(false)
const remember = ref(false)
const forgotVisible = ref(false)
const formRef = ref()
const form = reactive({ username: '', password: '', nickname: '', confirm: '' })

onMounted(() => {
  // 回填上次"记住密码"保存的账号
  const creds = readCreds()
  if (creds) {
    form.username = creds.username || ''
    form.password = creds.password || ''
    remember.value = true
  }
  if (auth.isLoggedIn) router.replace('/dashboard')
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }, { min: 3, message: '至少 3 个字符', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, message: '密码至少 6 位', trigger: 'blur' }],
  confirm: [
    {
      validator: (rule, value, cb) => {
        if (!isRegister.value) return cb()
        if (!value) return cb(new Error('请再次输入密码'))
        if (value !== form.password) return cb(new Error('两次输入的密码不一致'))
        cb()
      },
      trigger: 'blur'
    }
  ]
}

function toggle() {
  isRegister.value = !isRegister.value
  form.confirm = ''
}

async function submit() {
  try {
    await formRef.value.validate()
  } catch (e) {
    return
  }
  loading.value = true
  try {
    if (isRegister.value) {
      await auth.register({ username: form.username, password: form.password, nickname: form.nickname }, remember.value)
      writeCreds(remember.value ? { username: form.username, password: form.password } : null)
      ElMessage.success('注册成功，已自动登录')
    } else {
      await auth.login({ username: form.username, password: form.password }, remember.value)
      writeCreds(remember.value ? { username: form.username, password: form.password } : null)
      ElMessage.success(auth.isAdmin ? '欢迎回来，管理员' : '欢迎回来')
    }
    router.push(route.query.redirect || '/dashboard')
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '操作失败，请重试')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
/* 登录页保留该版本原始的靛蓝主色体系（登录入口独立于后台的 EP 蓝） */
.login-page {
  --el-color-primary: #4f46e5;
  --el-color-primary-light-3: #818cf8;
  --el-color-primary-light-5: #a5b4fc;
  --el-color-primary-light-7: #c7d2fe;
  --el-color-primary-light-8: #dbe3fe;
  --el-color-primary-light-9: #eef2ff;
  --el-color-primary-dark-2: #4338ca;
  --el-text-color-primary: #1f2937;
  --el-text-color-regular: #4b5563;
  --el-font-size-base: 13px;
}

@keyframes loginBgFlow {
  0% {
    transform: translate3d(-2%, -1%, 0) rotate(-4deg);
  }
  50% {
    transform: translate3d(3%, 2%, 0) rotate(3deg);
  }
  100% {
    transform: translate3d(-2%, -1%, 0) rotate(-4deg);
  }
}

@keyframes loginLineTravel {
  0% {
    transform: translateX(-18%) skewX(-18deg);
    opacity: 0.14;
  }
  45% {
    opacity: 0.42;
  }
  100% {
    transform: translateX(18%) skewX(-18deg);
    opacity: 0.14;
  }
}

@keyframes loginGridDrift {
  0% {
    background-position: 0 0, 0 0;
  }
  100% {
    background-position: 32px 24px, -28px 36px;
  }
}

@keyframes loginRiseIn {
  from {
    opacity: 0;
    transform: translateY(18px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

@keyframes loginLogoTilt {
  0%,
  100% {
    transform: rotate(0deg) scale(1);
  }
  35% {
    transform: rotate(7deg) scale(1.04);
  }
  65% {
    transform: rotate(-5deg) scale(0.99);
  }
}

@keyframes loginLoaderColor {
  0%,
  100% {
    border-radius: 18px;
    transform: rotate(0deg) scale(0.78);
  }
  50% {
    border-radius: 24px;
    transform: rotate(90deg) scale(1.02);
  }
}

@keyframes loginIconBeat {
  0%,
  100% {
    transform: translateY(0) scale(1);
  }
  45% {
    transform: translateY(-4px) scale(1.05);
  }
}

@keyframes loginTextMarquee {
  0% {
    transform: translateY(0);
  }
  24% {
    transform: translateY(0);
  }
  33% {
    transform: translateY(-25%);
  }
  57% {
    transform: translateY(-25%);
  }
  66% {
    transform: translateY(-50%);
  }
  90% {
    transform: translateY(-50%);
  }
  100% {
    transform: translateY(-75%);
  }
}

@keyframes loginTextBgSweep {
  0% {
    background-position: 0% 50%;
  }
  50% {
    background-position: 100% 50%;
  }
  100% {
    background-position: 0% 50%;
  }
}

@keyframes loginGlyphFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0) rotate(-8deg);
    opacity: 0.2;
  }
  50% {
    transform: translate3d(12px, -18px, 0) rotate(6deg);
    opacity: 0.34;
  }
}

@keyframes loginShimmer {
  0% {
    transform: translateX(-120%) skewX(-18deg);
  }
  100% {
    transform: translateX(180%) skewX(-18deg);
  }
}

@keyframes loginDecoFloat {
  0%,
  100% {
    transform: translate3d(0, 0, 0) rotate(var(--rot, -6deg));
  }
  50% {
    transform: translate3d(0, -22px, 0) rotate(calc(var(--rot, -6deg) + 2deg));
  }
}

.login-page::after {
  position: absolute;
  inset: 0;
  pointer-events: none;
  content: "";
  background:
    linear-gradient(115deg, transparent 0%, rgba(255, 255, 255, 0.4) 42%, transparent 56%),
    radial-gradient(circle at 72% 16%, rgba(59, 130, 246, 0.16), transparent 32%);
  opacity: 0.8;
}

/* ===== 背景层次 ===== */
.login-aurora {
  position: absolute;
  width: 76vw;
  height: 46vh;
  pointer-events: none;
  border-radius: 42% 58% 55% 45%;
  filter: blur(52px);
  opacity: 0.6;
  animation: loginBgFlow 16s ease-in-out infinite;
}

.login-aurora-a {
  top: -16vh;
  left: -16vw;
  background: linear-gradient(110deg, rgba(96, 165, 250, 0.5), rgba(125, 211, 252, 0.22), transparent);
}

.login-aurora-b {
  right: -20vw;
  bottom: -18vh;
  background: linear-gradient(110deg, transparent, rgba(129, 140, 248, 0.3), rgba(251, 191, 36, 0.22));
  animation-duration: 19s;
  animation-direction: reverse;
}

.login-aurora-c {
  left: 26%;
  top: 8%;
  width: 46vw;
  height: 34vh;
  background: linear-gradient(120deg, rgba(191, 219, 254, 0.4), transparent 70%);
  animation-duration: 24s;
}

/* 左区聚光灯：给内容一个视觉重心 */
.login-spotlight {
  position: absolute;
  left: 2%;
  top: 12%;
  width: 52vw;
  height: 76vh;
  pointer-events: none;
  background: radial-gradient(closest-side, rgba(255, 255, 255, 0.85), rgba(219, 234, 254, 0.28) 62%, transparent);
  filter: blur(10px);
  opacity: 0.9;
}

.login-flow-line {
  position: absolute;
  left: 4%;
  right: 4%;
  height: 1px;
  pointer-events: none;
  background: linear-gradient(90deg, transparent, rgba(37, 99, 235, 0.22), rgba(14, 165, 233, 0.34), transparent);
  animation: loginLineTravel 10s ease-in-out infinite;
}

.login-flow-line-a {
  top: 26%;
}

.login-flow-line-b {
  bottom: 22%;
  animation-delay: -4s;
  animation-duration: 13s;
}

.login-drift-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  opacity: 0.2;
  background-image:
    linear-gradient(rgba(30, 41, 59, 0.09) 1px, transparent 1px),
    linear-gradient(90deg, rgba(30, 41, 59, 0.09) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: linear-gradient(90deg, rgba(0, 0, 0, 0.9), rgba(0, 0, 0, 0.35) 62%, transparent 92%);
  animation: loginGridDrift 18s linear infinite;
}

.login-glyph {
  position: absolute;
  z-index: 0;
  pointer-events: none;
  color: rgba(37, 99, 235, 0.22);
  font-size: 44px;
  font-weight: 800;
  line-height: 1;
  text-shadow: 0 18px 38px rgba(59, 130, 246, 0.14);
  animation: loginGlyphFloat 9s ease-in-out infinite;
}

.login-glyph-a {
  top: 16%;
  left: 38%;
}

.login-glyph-b {
  right: 9%;
  bottom: 15%;
  color: rgba(79, 70, 229, 0.2);
  animation-delay: -2.8s;
}

.login-glyph-c {
  left: 7%;
  bottom: 12%;
  color: rgba(245, 158, 11, 0.22);
  animation-delay: -5.4s;
}

/* ===== 背景悬浮素材卡 ===== */
.deco-layer {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 0;
}

.deco-card {
  position: absolute;
  width: 168px;
  padding: 12px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.38);
  border: 1px solid rgba(255, 255, 255, 0.55);
  box-shadow:
    0 20px 44px -18px rgba(59, 73, 158, 0.14),
    inset 0 1px 0 rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(6px);
  animation: loginDecoFloat 9s ease-in-out infinite;
}

.deco-thumb {
  width: 100%;
  height: 74px;
  border-radius: 12px;
  margin-bottom: 10px;
}

.deco-line {
  height: 7px;
  border-radius: 999px;
  background: rgba(148, 163, 184, 0.42);
  margin-bottom: 7px;
}

.deco-line.short {
  opacity: 0.6;
}

.t-blue {
  background: linear-gradient(135deg, #bfdbfe, #60a5fa 55%, #3b82f6);
}

.t-indigo {
  background: linear-gradient(135deg, #c7d2fe, #818cf8 55%, #4f46e5);
}

.t-amber {
  background: linear-gradient(135deg, #fde68a, #fbbf24 55%, #f59e0b);
}

.t-emerald {
  background: linear-gradient(135deg, #a7f3d0, #34d399 55%, #10b981);
}

.deco-1 {
  left: 3.5%;
  top: 12%;
  --rot: -7deg;
  opacity: 0.34;
}

.deco-2 {
  left: 7%;
  bottom: 13%;
  --rot: 5deg;
  width: 150px;
  opacity: 0.3;
  animation-delay: -3s;
}

.deco-3 {
  right: 4%;
  top: 13%;
  --rot: 9deg;
  width: 146px;
  opacity: 0.28;
  animation-delay: -5.5s;
}

.deco-4 {
  right: 8%;
  bottom: 14%;
  --rot: -5deg;
  width: 176px;
  opacity: 0.26;
  animation-delay: -1.8s;
}

/* ===== 入场节奏 ===== */
.login-brand-title,
.login-brand-subtitle,
.login-feature,
.login-card {
  opacity: 0;
  animation: loginRiseIn 0.72s cubic-bezier(0.22, 1, 0.36, 1) forwards;
}

.login-brand-subtitle {
  animation-delay: 0.08s;
}

.login-feature:nth-of-type(1) {
  animation-delay: 0.16s;
}

.login-feature:nth-of-type(2) {
  animation-delay: 0.26s;
}

.login-feature:nth-of-type(3) {
  animation-delay: 0.36s;
}

/* ===== 登录卡：立体质感 ===== */
.login-card-wrap {
  position: relative;
  z-index: 10;
  width: 100%;
  max-width: 430px;
  transition: transform 0.4s cubic-bezier(0.22, 1, 0.36, 1);
}

.login-card-wrap:hover {
  transform: translateY(-5px);
}

.login-card {
  overflow: hidden;
  isolation: isolate;
  border-radius: 26px;
  background: linear-gradient(158deg, rgba(255, 255, 255, 0.94) 0%, rgba(255, 255, 255, 0.8) 46%, rgba(238, 242, 255, 0.72) 100%);
  backdrop-filter: blur(24px) saturate(160%);
  -webkit-backdrop-filter: blur(24px) saturate(160%);
  border: 1px solid rgba(255, 255, 255, 0.9);
  box-shadow:
    inset 0 1px 0 0 rgba(255, 255, 255, 0.95),
    inset 0 -22px 40px -30px rgba(79, 70, 229, 0.45),
    0 1px 2px rgba(15, 23, 42, 0.06),
    0 14px 28px -14px rgba(79, 70, 229, 0.22),
    0 44px 80px -32px rgba(15, 23, 42, 0.38);
  animation: loginRiseIn 0.76s cubic-bezier(0.22, 1, 0.36, 1) 0.12s forwards;
}

/* 卡片背后的彩色柔光，强化悬浮感 */
.card-accent {
  position: absolute;
  inset: -6% -8% -13% -8%;
  z-index: -1;
  pointer-events: none;
  border-radius: 44px;
  background:
    radial-gradient(58% 52% at 28% 22%, rgba(129, 140, 248, 0.3), transparent 70%),
    radial-gradient(52% 48% at 76% 82%, rgba(56, 189, 248, 0.24), transparent 72%),
    radial-gradient(46% 42% at 62% 8%, rgba(192, 132, 252, 0.2), transparent 70%);
  filter: blur(16px);
}

.login-card::after {
  position: absolute;
  top: 0;
  bottom: 0;
  left: 0;
  width: 46%;
  pointer-events: none;
  content: "";
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.26), transparent);
  animation: loginShimmer 5.8s ease-in-out infinite;
}

/* ===== 记住密码 / 忘记密码 ===== */
.login-form-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -6px 0 14px;
}

.login-card :deep(.el-checkbox) {
  height: 20px;
  margin-right: 0;
}

.login-card :deep(.el-checkbox__label) {
  padding-left: 7px;
  font-size: 13px;
  color: #64748b;
}

.login-card :deep(.el-checkbox__inner) {
  width: 15px;
  height: 15px;
  border-color: #cbd5e1;
  border-radius: 4px;
}

.login-forget-link {
  font-size: 13px;
  color: #4f46e5;
  cursor: pointer;
  user-select: none;
  transition: color 0.2s ease;
}

.login-forget-link:hover {
  color: #4338ca;
  text-decoration: underline;
}

/* ===== 忘记密码弹窗 ===== */
.login-page :deep(.el-dialog) {
  border-radius: 18px;
  box-shadow: 0 32px 72px -26px rgba(15, 23, 42, 0.42);
}

.forgot-body {
  font-size: 13.5px;
  line-height: 1.8;
  color: #475569;
}

.forgot-body p {
  margin: 0 0 8px;
}

.forgot-steps {
  margin: 0 0 12px;
  padding-left: 20px;
}

.forgot-steps li {
  margin-bottom: 4px;
}

.forgot-body code {
  padding: 1px 5px;
  border-radius: 5px;
  background: #eef2ff;
  color: #4338ca;
  font-family: Consolas, Menlo, monospace;
  font-size: 12px;
}

/* ===== Logo ===== */
.login-logo {
  position: relative;
  display: flex;
  width: 84px;
  height: 84px;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  margin-right: 22px;
  border-radius: 28px;
  isolation: isolate;
}

.login-logo .loader_cube {
  position: absolute;
  inset: 8px;
  border: 0;
  border-radius: 22px;
}

.login-logo .loader_cube--color {
  z-index: 1;
  background: linear-gradient(135deg, #36dff8 0%, #5f7cff 52%, #d946ef 100%);
  animation: loginLoaderColor 2.8s ease-in-out infinite;
}

.login-logo .loader_cube--glowing {
  z-index: 2;
  background-color: rgba(255, 255, 255, 0.14);
  box-shadow: inset 0 0 14px rgba(255, 255, 255, 0.18);
  backdrop-filter: blur(3px);
}

.login-logo svg {
  position: relative;
  z-index: 3;
}

.login-brand-text {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.login-brand-name {
  min-width: max-content;
  margin: 0 0 8px;
  font-size: clamp(1.9rem, 2.4vw, 2.5rem);
  line-height: 1.12;
  white-space: nowrap;
}

/* ===== 副标题 + 竖向跑马灯 ===== */
.login-brand-subtitle {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  width: fit-content;
  max-width: 560px;
  min-height: 40px;
  padding: 0 14px;
  border-radius: 12px;
  background: linear-gradient(90deg, rgba(255, 255, 255, 0.22), rgba(219, 234, 254, 0.55), rgba(255, 255, 255, 0.22));
  background-size: 220% 100%;
  color: #64748b;
  font-size: 18px;
  animation: loginRiseIn 0.72s cubic-bezier(0.22, 1, 0.36, 1) forwards, loginTextBgSweep 7s ease-in-out infinite;
  white-space: nowrap;
}

.login-marquee-vertical {
  position: relative;
  display: inline-block;
  width: 230px;
  height: 28px;
  overflow: hidden;
  color: #2563eb;
  font-weight: 700;
  vertical-align: middle;
}

.login-marquee-stack {
  display: flex;
  flex-direction: column;
  height: 400%;
  animation: loginTextMarquee 7.2s cubic-bezier(0.8, 0, 0.2, 1) infinite;
}

.login-marquee-stack > span {
  display: flex;
  height: 25%;
  align-items: center;
  white-space: nowrap;
}

/* ===== 特性行 ===== */
.login-feature {
  position: relative;
  gap: 16px;
  padding: 6px 0;
}

.login-feature-icon {
  width: 48px !important;
  height: 48px !important;
  border-radius: 16px !important;
  background: linear-gradient(145deg, rgba(255, 255, 255, 0.72), rgba(239, 246, 255, 0.48)) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.86),
    0 10px 22px rgba(37, 99, 235, 0.08);
  animation: loginIconBeat 2.9s ease-in-out infinite;
}

.login-feature-icon svg {
  width: 23px;
  height: 23px;
  stroke-width: 2.2;
}

.login-feature h3 {
  color: #1e293b;
  font-size: 17px;
  line-height: 24px;
  font-weight: 700;
}

.login-feature p {
  color: #64748b;
  font-size: 13.5px;
  line-height: 20px;
}

.login-feature:nth-of-type(1) .login-feature-icon {
  background: linear-gradient(145deg, #eff6ff, #dbeafe) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 12px 24px rgba(37, 99, 235, 0.18);
}

.login-feature:nth-of-type(2) .login-feature-icon {
  background: linear-gradient(145deg, #eef2ff, #e0e7ff) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 12px 24px rgba(79, 70, 229, 0.18);
}

.login-feature:nth-of-type(3) .login-feature-icon {
  background: linear-gradient(145deg, #fffbeb, #fef3c7) !important;
  box-shadow:
    inset 0 1px 0 rgba(255, 255, 255, 0.9),
    0 12px 24px rgba(245, 158, 11, 0.18);
}

.login-feature:nth-of-type(2) .login-feature-icon {
  animation-delay: 0.22s;
}

.login-feature:nth-of-type(3) .login-feature-icon {
  animation-delay: 0.44s;
}

/* ===== 面板切换动画 ===== */
.login-panel-swap {
  animation: loginRiseIn 0.34s ease-out both;
}

.login-register-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  line-height: 22px;
}

.login-card :deep(.login-inline-link.el-button) {
  display: inline-flex;
  width: auto;
  height: 22px;
  min-height: 0;
  padding: 0;
  vertical-align: middle;
}

/* ===== 输入框 ===== */
.login-card :deep(.el-input__wrapper) {
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.88);
  transition:
    transform 0.18s ease,
    background-color 0.18s ease,
    box-shadow 0.18s ease;
}

.login-card :deep(.el-input__wrapper:hover),
.login-card :deep(.el-input__wrapper.is-focus) {
  transform: translateY(-1px);
  background: #ffffff;
  box-shadow:
    0 0 0 1px rgba(59, 130, 246, 0.48) inset,
    0 10px 24px rgba(59, 130, 246, 0.1) !important;
}

/* ===== 主按钮：渐变 + 扫光 ===== */
.login-card :deep(.el-button--primary:not(.is-link)) {
  position: relative;
  overflow: hidden;
  border: 0;
  border-radius: 13px;
  background: linear-gradient(135deg, #2563eb 0%, #4f46e5 100%) !important;
  box-shadow: 0 12px 22px rgba(37, 99, 235, 0.24);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    filter 0.18s ease;
}

.login-card :deep(.el-button--primary:not(.is-link):hover) {
  transform: translateY(-2px);
  box-shadow: 0 16px 30px rgba(37, 99, 235, 0.3);
  filter: saturate(1.08);
}

.login-card :deep(.el-button--primary:not(.is-link):active) {
  transform: translateY(0);
}

.login-card :deep(.el-button--primary:not(.is-link)::before) {
  position: absolute;
  top: 0;
  bottom: 0;
  left: -45%;
  width: 38%;
  content: "";
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.34), transparent);
  transform: skewX(-18deg);
}

.login-card :deep(.el-button--primary:not(.is-link):hover::before) {
  animation: loginShimmer 0.95s ease;
}

.el-form-item {
  margin-bottom: 22px !important;
}

/* 卡片底部说明 */
.login-foot-note {
  margin-top: 18px;
  text-align: center;
  font-size: 12px;
  color: #94a3b8;
}

@media (prefers-reduced-motion: reduce) {
  .login-aurora,
  .login-flow-line,
  .login-drift-grid,
  .login-brand-title,
  .login-brand-subtitle,
  .login-feature,
  .login-card,
  .login-logo,
  .login-glyph,
  .deco-card,
  .login-card::after {
    animation: none !important;
    opacity: 1;
  }

  .login-feature,
  .login-card :deep(.el-input__wrapper),
  .login-card :deep(.el-button--primary:not(.is-link)) {
    transition: none !important;
  }
}
</style>
