<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import WorldBuilding from './components/WorldBuilding.vue'
import { type AppLanguage, type AppTheme, getSettings } from './lib/api'
import { ensureGuestUser } from './lib/guestSession'
import { useTabManager } from './lib/tabManager'

const router = useRouter()
const route = useRoute()
const { otherTabActive, forceActivateTab } = useTabManager()

const loading = ref(true)
const currentLang = ref<AppLanguage>('en-US')
const showMenu = ref(false)
const showWorldBuilding = ref(true)

const translations = {
  'en-US': {
    home: 'Home',
    worlds: 'Worlds',
    create: 'Create',
    settings: 'Settings',
    menu: 'Menu'
  },
  'zh-CN': {
    home: '首页',
    worlds: '世界列表',
    create: '创建',
    settings: '设置',
    menu: '菜单'
  }
}

const shouldShowMenu = computed(() => route.name !== 'landing')
let currentThemeSetting: AppTheme = 'system'

const t = (key: keyof typeof translations['en-US']) => translations[currentLang.value][key]

const applyTheme = (theme: AppTheme) => {
  document.documentElement.classList.remove('theme-light', 'theme-dark')
  if (theme === 'light') {
    document.documentElement.classList.add('theme-light')
    return
  }
  if (theme === 'dark') {
    document.documentElement.classList.add('theme-dark')
    return
  }

  const prefersDark = window.matchMedia?.('(prefers-color-scheme: dark)').matches
  document.documentElement.classList.add(prefersDark ? 'theme-dark' : 'theme-light')
}

const loadPreferences = async () => {
  const guestUserId = await ensureGuestUser()
  const settings = await getSettings(guestUserId)

  if (settings.language) {
    currentLang.value = settings.language
    localStorage.setItem('preferredLanguage', settings.language)
  }

  if (settings.theme) {
    currentThemeSetting = settings.theme
    localStorage.setItem('preferredTheme', settings.theme)
    applyTheme(settings.theme)
  } else {
    const savedTheme = localStorage.getItem('preferredTheme') as AppTheme | null
    currentThemeSetting = savedTheme || 'system'
    applyTheme(currentThemeSetting)
  }
}

onMounted(async () => {
  const savedLang = localStorage.getItem('preferredLanguage') as AppLanguage | null
  if (savedLang === 'en-US' || savedLang === 'zh-CN') {
    currentLang.value = savedLang
  }

  try {
    await loadPreferences()
  } catch (error) {
    console.warn('Failed to load preferences, using local fallbacks.', error)
    const savedTheme = localStorage.getItem('preferredTheme') as AppTheme | null
    currentThemeSetting = savedTheme || 'system'
    applyTheme(currentThemeSetting)
  }

  if (window.matchMedia) {
    const darkModeQuery = window.matchMedia('(prefers-color-scheme: dark)')
    darkModeQuery.addEventListener('change', () => {
      if (currentThemeSetting === 'system') {
        applyTheme('system')
      }
    })
  }

  document.addEventListener('click', event => {
    const menu = document.querySelector('.menu-container')
    if (menu && !menu.contains(event.target as Node)) {
      showMenu.value = false
    }
  })

  loading.value = false
})

watch(
  () => route.path,
  () => {
    showMenu.value = false
    showWorldBuilding.value = route.name === 'world'
  }
)

const handleLanguageChange = (lang: AppLanguage) => {
  currentLang.value = lang
  localStorage.setItem('preferredLanguage', lang)
}

const handleThemeChange = (theme: AppTheme) => {
  currentThemeSetting = theme
  localStorage.setItem('preferredTheme', theme)
  applyTheme(theme)
}
</script>

<template>
  <div v-if="!loading">
    <div v-if="otherTabActive" class="inactive-tab-warning">
      <div class="warning-content">
        <div class="warning-icon">!</div>
        <div class="warning-message">
          {{ currentLang === 'en-US'
            ? 'This tab is inactive. Another tab is currently active.'
            : '此标签页当前处于非活动状态，另一个标签页正在控制会话。' }}
        </div>
        <button class="activate-button" @click="forceActivateTab">
          {{ currentLang === 'en-US' ? 'Activate This Tab' : '激活此标签页' }}
        </button>
      </div>
    </div>

    <div v-if="shouldShowMenu" class="header">
      <div class="menu-container">
        <button class="menu-button" @click="showMenu = !showMenu">
          {{ t('menu') }}
        </button>
      </div>
    </div>

    <transition name="menu-fade">
      <div v-if="showMenu" class="menu-overlay" @click.self="showMenu = false">
        <div class="menu-panel">
          <router-link class="menu-link" :to="{ name: 'landing' }">{{ t('home') }}</router-link>
          <router-link class="menu-link" :to="{ name: 'worlds' }">{{ t('worlds') }}</router-link>
          <router-link class="menu-link" :to="{ name: 'create' }">{{ t('create') }}</router-link>
          <router-link class="menu-link" :to="{ name: 'settings' }">{{ t('settings') }}</router-link>
        </div>
      </div>
    </transition>

    <div v-if="route.name === 'world' && showWorldBuilding" class="world-building-wrapper">
      <WorldBuilding
        :current-lang="currentLang"
        @story-completed="showWorldBuilding = false"
      />
    </div>

    <div v-else class="main-content">
      <router-view
        v-slot="{ Component }"
        :current-lang="currentLang"
        @view-story="(story: any) => router.push({ name: 'world', params: { id: story.id } })"
        @navigate="(view: string, id?: string) => id ? router.push({ name: view, params: { id } }) : router.push({ name: view })"
        @story-created="(story: any) => router.push({ name: 'world', params: { id: story.id } })"
        @language-change="handleLanguageChange"
        @theme-change="handleThemeChange"
      >
        <component
          :is="Component"
          :current-lang="currentLang"
          @view-story="(story: any) => router.push({ name: 'world', params: { id: story.id } })"
          @navigate="(view: string, id?: string) => id ? router.push({ name: view, params: { id } }) : router.push({ name: view })"
          @story-created="(story: any) => router.push({ name: 'world', params: { id: story.id } })"
          @language-change="handleLanguageChange"
          @theme-change="handleThemeChange"
        />
      </router-view>
    </div>
  </div>
</template>

<style scoped>
.header {
  position: fixed;
  top: 20px;
  right: 20px;
  z-index: 100;
}

.menu-button {
  border: 1px solid currentColor;
  background: transparent;
  padding: 10px 14px;
  font-family: monospace;
  cursor: pointer;
  color: inherit;
}

.menu-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.12);
  z-index: 90;
}

.menu-panel {
  position: absolute;
  top: 70px;
  right: 20px;
  width: 220px;
  display: grid;
  gap: 8px;
  padding: 16px;
  background: var(--menu-bg, #ffffff);
  border: 1px solid var(--menu-border, #d9d9d9);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
}

.menu-link {
  padding: 10px 12px;
  color: inherit;
  text-decoration: none;
  border: 1px solid transparent;
}

.menu-link:hover {
  border-color: currentColor;
}

.main-content {
  min-height: 100vh;
}

.inactive-tab-warning {
  position: fixed;
  inset: 0;
  z-index: 200;
  background: rgba(0, 0, 0, 0.75);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
}

.warning-content {
  max-width: 420px;
  width: 100%;
  background: #111111;
  color: #f7f7f7;
  padding: 24px;
  border: 1px solid #3d3d3d;
  text-align: center;
  font-family: monospace;
}

.warning-icon {
  font-size: 28px;
  margin-bottom: 16px;
}

.warning-message {
  line-height: 1.6;
  margin-bottom: 16px;
}

.activate-button {
  border: 1px solid #f7f7f7;
  background: transparent;
  color: inherit;
  padding: 10px 14px;
  cursor: pointer;
  font-family: inherit;
}

.menu-fade-enter-active,
.menu-fade-leave-active {
  transition: opacity 0.2s ease;
}

.menu-fade-enter-from,
.menu-fade-leave-to {
  opacity: 0;
}

:global(.theme-light) {
  --menu-bg: #ffffff;
  --menu-border: #d9d9d9;
}

:global(.theme-dark) {
  --menu-bg: #181818;
  --menu-border: #3a3a3a;
}
</style>
