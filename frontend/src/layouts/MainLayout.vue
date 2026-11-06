<template>
  <div class="main-layout">
    <!-- 侧边栏 -->
    <aside class="sidebar">
      <div class="logo">
        <div class="logo-icon">HR</div>
        <span class="logo-text">{{ $t('app.title') }}</span>
      </div>
      <div class="nav-divider" />
      <nav class="nav-menu" :aria-label="locale === 'zh-CN' ? '主导航' : 'Main navigation'">
        <router-link
          v-for="item in menuItems"
          :key="item.path"
          :to="item.path"
          :aria-label="item.name"
          :title="item.name"
          class="nav-item"
          :class="{ active: isActive(item.path) }"
        >
          <el-icon><component :is="item.icon" /></el-icon>
          <span>{{ item.name }}</span>
        </router-link>
      </nav>

      <!-- 语言切换 -->
      <div class="lang-switch">
        <button
          aria-label="Chinese"
          :class="['lang-btn', { active: locale === 'zh-CN' }]"
          @click="toggleLang('zh-CN')"
        >
          <span class="lang-full">Chinese</span>
          <span class="lang-short">中</span>
        </button>
        <button
          aria-label="English"
          :class="['lang-btn', { active: locale === 'en' }]"
          @click="toggleLang('en')"
        >
          <span class="lang-full">English</span>
          <span class="lang-short">EN</span>
        </button>
      </div>


    </aside>

    <!-- 主内容区 -->
    <main class="main-content">
      <header class="page-header">
        <div class="page-heading">
          <h1 class="page-title">{{ currentTitle }}</h1>
          <p v-if="currentDescription" class="page-description" :title="currentDescription">
            {{ currentDescription }}
          </p>
        </div>
        <div class="header-actions">
          <el-dropdown trigger="click" placement="bottom-end" @command="handleAccountCommand">
            <button class="account-button" :aria-label="accountMenuLabel" :title="account?.email">
              <span class="account-info">
                <span class="account-name">{{ account?.email }}</span>
                <span class="account-role">{{ accountRole }}</span>
              </span>
              <span class="account-avatar" aria-hidden="true">{{ accountInitial }}</span>
              <el-icon class="account-chevron"><ArrowDown /></el-icon>
            </button>
            <template #dropdown>
              <el-dropdown-menu class="account-dropdown">
                <el-dropdown-item disabled><span class="dropdown-account">{{ account?.email }}</span></el-dropdown-item>
                <el-dropdown-item command="password" divided :icon="Lock">{{ locale === 'zh-CN' ? '修改密码' : 'Change password' }}</el-dropdown-item>
                <el-dropdown-item command="logout" :icon="SwitchButton">{{ locale === 'zh-CN' ? '退出登录' : 'Sign out' }}</el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </header>
      <div class="content-area">
        <router-view />
      </div>
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useI18n } from 'vue-i18n'
import { Upload, Document, Files, Collection, Notebook, UserFilled, ArrowDown, Lock, SwitchButton, FolderOpened, Briefcase } from '@element-plus/icons-vue'
import { switchLanguage } from '@/locales'
import { account, signOut, canUse } from '@/stores/auth'

const { t, locale } = useI18n()
const route = useRoute()
const router = useRouter()
const accountInitial = computed(() => Array.from(account.value?.email || 'U')[0].toUpperCase())
const accountRole = computed(() => account.value?.role === 'admin'
  ? (locale.value === 'zh-CN' ? '管理员' : 'Administrator')
  : (locale.value === 'zh-CN' ? '普通用户' : 'Member'))
const accountMenuLabel = computed(() => `${locale.value === 'zh-CN' ? '账号菜单' : 'Account menu'} · ${account.value?.email || ''}`)
function handleAccountCommand(command: string) {
  if (command === 'password') void router.push('/change-password')
  if (command === 'logout') void signOut()
}

const menuItems = computed(() => [
  { path: '/upload', name: t('nav.uploadConfig'), icon: Upload },
  { path: '/history', name: t('nav.history'), icon: Document },
  { path: '/templates', name: t('nav.templates'), icon: Files },
  { path: '/cv-library', name: t('nav.cvLibrary'), icon: FolderOpened },
  { path: '/jd-library', name: t('nav.jdLibrary'), icon: Collection },
  { path: '/terminology', name: t('nav.terminology'), icon: Notebook },
  { path: '/recruitment-tools', name: t('nav.recruitmentTools'), icon: Briefcase },
  { path: '/offboarding-tools', name: t('nav.offboardingTools'), icon: SwitchButton },
  ...(account.value?.role === 'admin' ? [{ path: '/admin', name: '管理后台', icon: UserFilled }] : [])
].filter(item => {
  const features: Record<string, string> = { '/cv-library': 'cv', '/templates': 'templates', '/jd-library': 'library', '/terminology': 'terminology' }
  return !features[item.path] || canUse(features[item.path])
}))

function isActive(path: string): boolean {
  return route.path === path || route.path.startsWith(path + '/')
}

function toggleLang(lang: 'zh-CN' | 'en') {
  switchLanguage(lang)
}

const currentTitle = computed(() => {
  const item = menuItems.value.find(m => isActive(m.path))
  return item?.name || ''
})

const currentDescription = computed(() => {
  const descKeyMap: Record<string, string> = {
    '/upload': 'router.uploadDesc',
    '/history': 'router.historyDesc',
    '/templates': 'router.templatesDesc',
    '/cv-library': 'router.cvLibraryDesc',
    '/jd-library': 'router.jdLibraryDesc',
    '/terminology': 'router.terminologyDesc'
  }
  const key = descKeyMap[route.path]
  return key ? t(key) : ''
})
</script>

<style scoped>
.main-layout {
  display: flex;
  height: 100dvh;
  background: #1E1E2D;
  overflow: hidden;
}
.sidebar {
  width: 216px;
  min-width: 216px;
  display: flex;
  flex-direction: column;
  padding: 24px 0 18px;
  background: #1E1E2D;
}
.logo { display: flex; align-items: center; gap: 10px; padding: 0 20px 24px; }
.logo-icon {
  display: flex; align-items: center; justify-content: center; flex-shrink: 0;
  width: 38px; height: 38px; border-radius: 10px;
  background: linear-gradient(135deg, var(--app-primary), var(--app-primary-dark));
  color: #fff; font-size: 14px; font-weight: 700;
}
.logo-text { color: #fff; font-size: 15px; font-weight: 600; letter-spacing: .02em; }
.nav-divider { height: 1px; background: #3A3A52; margin: 0 20px 18px; opacity: .6; }
.nav-menu { flex: 1; min-height: 0; overflow-y: auto; display: flex; flex-direction: column; gap: 8px; padding: 0 12px; }
.nav-item {
  position: relative; display: flex; align-items: center; flex-shrink: 0; gap: 13px;
  min-height: 46px; box-sizing: border-box; padding: 11px 16px;
  color: #9696AC; text-decoration: none; border: 1px solid transparent; border-radius: 11px;
  font-size: 14px; transition: color .18s, background-color .18s, border-color .18s;
}
.nav-item .el-icon { font-size: 20px; flex-shrink: 0; }
.nav-item:hover { color: #fff; background-color: rgba(var(--app-primary-rgb), .12); }
.nav-item.active {
  color: #fff; font-weight: 600;
  background: linear-gradient(100deg, rgba(var(--app-primary-rgb), .56) 0%, rgba(var(--app-primary-rgb), .27) 58%, rgba(var(--app-primary-dark-rgb), .13) 100%);
  border-color: rgba(var(--app-primary-rgb), .19);
}
.nav-item.active .el-icon { color: var(--app-primary-light-7); }
.nav-item.active::before { content: ''; position: absolute; left: -1px; top: 13px; bottom: 13px; width: 3px; border-radius: 4px; background: var(--app-primary-light-3); }
.nav-item:focus-visible, .lang-btn:focus-visible, .account-button:focus-visible { outline: 2px solid var(--app-primary-light-3); outline-offset: 3px; }
.lang-switch { display: flex; gap: 6px; padding: 18px 20px 0; margin-top: auto; }
.lang-btn { flex: 1; padding: 7px 4px; border: 1px solid #3A3A55; border-radius: 6px; background: transparent; color: #AAAAC2; font-size: 11px; font-weight: 600; cursor: pointer; white-space: nowrap; }
.lang-btn:hover { border-color: var(--app-primary); color: #fff; }
.lang-btn.active { background: var(--app-primary); border-color: var(--app-primary); color: #fff; }
.lang-short { display: none; }
.main-content { min-width: 0; min-height: 0; flex: 1; display: flex; flex-direction: column; overflow: hidden; background: #F0F2F5; border-top-left-radius: 26px; }
.page-header { display: flex; align-items: center; justify-content: space-between; gap: 24px; box-sizing: border-box; min-height: 68px; padding: 12px 24px; background: #fff; border-bottom: 1px solid #E8ECF3; flex-shrink: 0; }
.page-heading { min-width: 0; }
.page-title { margin: 0; color: #1E1E2D; font-size: 18px; line-height: 1.4; font-weight: 600; }
.page-description { margin: 3px 0 0; color: #9696AC; font-size: 11px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.header-actions { flex-shrink: 0; padding-left: 22px; border-left: 1px solid #E8ECF3; }
.account-button { display: flex; align-items: center; gap: 12px; padding: 3px 0 3px 8px; background: none; border: 0; border-radius: 8px; color: #1E1E2D; font: inherit; cursor: pointer; }
.account-info { display: flex; flex-direction: column; align-items: flex-end; gap: 3px; min-width: 0; }
.account-name { max-width: 230px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; font-size: 13px; font-weight: 500; }
.account-role { font-size: 10px; color: #9696AC; }
.account-avatar { display: flex; align-items: center; justify-content: center; flex-shrink: 0; width: 38px; height: 38px; border-radius: 50%; background: var(--app-primary-soft); border: 2px solid var(--app-primary-light-8); color: var(--app-primary); font-size: 16px; font-weight: 600; }
.account-button:hover .account-avatar { border-color: var(--app-primary); }
.account-chevron { font-size: 12px; color: #9696AC; }
.dropdown-account { display: inline-block; max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.content-area { min-width: 0; min-height: 0; flex: 1; padding: 14px 18px; overflow: hidden; }
@media (max-height: 760px) and (min-width: 761px) {
  .sidebar { padding-top: 18px; }
  .logo { padding-bottom: 18px; }
  .nav-menu { gap: 5px; }
  .nav-item { min-height: 42px; padding-top: 9px; padding-bottom: 9px; }
  .page-header { min-height: 58px; padding-top: 7px; padding-bottom: 7px; }
  .content-area { padding: 8px 12px; }
}
@media (max-width: 1000px) {
  .sidebar { width: 188px; min-width: 188px; }
  .logo { padding-left: 16px; padding-right: 12px; }
  .logo-text { font-size: 13px; }
  .account-name { max-width: 170px; }
  .page-header { gap: 16px; padding-left: 18px; padding-right: 18px; }
}
@media (max-width: 760px) {
  .sidebar { width: 58px; min-width: 58px; padding: 14px 0; }
  .logo { justify-content: center; padding: 0 0 16px; }
  .logo-icon { width: 34px; height: 34px; }
  .logo-text, .nav-item>span { display: none; }
  .nav-divider { margin: 0 10px 12px; }
  .nav-menu { padding: 0 6px; gap: 8px; }
  .nav-item { justify-content: center; padding: 11px 0; min-height: 44px; border-radius: 9px; }
  .lang-switch { flex-direction: column; gap: 5px; padding: 14px 7px 0; }
  .lang-btn { padding: 6px 0; font-size: 10px; }
  .lang-full { display: none; }
  .lang-short { display: inline; }
  .main-content { border-top-left-radius: 18px; }
  .page-header { min-height: 62px; padding: 9px 12px; gap: 8px; }
  .page-title { font-size: 15px; }
  .page-description { display: none; }
  .header-actions { padding-left: 8px; }
  .account-button { gap: 7px; padding-left: 0; }
  .account-name { max-width: 100px; font-size: 11px; }
  .account-avatar { width: 30px; height: 30px; font-size: 13px; }
  .account-chevron { display: none; }
  .content-area { padding: 8px; overflow-y: auto; overflow-x: hidden; }
}
@media (prefers-reduced-motion: reduce) { .nav-item { transition: none; } }
</style>
