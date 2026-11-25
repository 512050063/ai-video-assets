import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import 'element-plus/dist/index.css'
import 'element-plus/theme-chalk/dark/css-vars.css'
import './style.css'
import App from './App.vue'
import router from './router'
import GridSkeleton from './components/ui/GridSkeleton.vue'
import { usePermissionStore } from './stores/permission'

const app = createApp(App)
const pinia = createPinia()
app.use(pinia)
app.use(router)
app.use(ElementPlus, { locale: zhCn })
// 栅格骨架为全站通用加载反馈，统一注册，页面直接以 <GridSkeleton /> 使用
app.component('GridSkeleton', GridSkeleton)

// 模块角色权限在挂载前加载完成，避免菜单与按钮先渲染空白再闪现
const perm = usePermissionStore(pinia)
perm.load().finally(() => {
  app.mount('#app')
})
