<template>
  <section class="settings-container">
    <div class="settings-shell">
      <div>
        <p class="eyebrow">{{ t('eyebrow') }}</p>
        <h1>{{ t('title') }}</h1>
        <p class="subtitle">{{ t('subtitle') }}</p>
      </div>

      <div class="panel">
        <div class="setting-block">
          <label>{{ t('language') }}</label>
          <div class="option-row">
            <button
              class="option-button"
              :class="{ active: currentLang === 'en-US' }"
              @click="changeLanguage('en-US')"
            >
              English
            </button>
            <button
              class="option-button"
              :class="{ active: currentLang === 'zh-CN' }"
              @click="changeLanguage('zh-CN')"
            >
              中文
            </button>
          </div>
        </div>

        <div class="setting-block">
          <label>{{ t('theme') }}</label>
          <div class="option-row">
            <button
              class="option-button"
              :class="{ active: currentTheme === 'system' }"
              @click="changeTheme('system')"
            >
              {{ t('system') }}
            </button>
            <button
              class="option-button"
              :class="{ active: currentTheme === 'light' }"
              @click="changeTheme('light')"
            >
              {{ t('light') }}
            </button>
            <button
              class="option-button"
              :class="{ active: currentTheme === 'dark' }"
              @click="changeTheme('dark')"
            >
              {{ t('dark') }}
            </button>
          </div>
        </div>

        <div class="setting-block guest-note">
          <label>{{ t('mode') }}</label>
          <p>{{ t('guestNotice') }}</p>
        </div>
      </div>
    </div>

    <Notification
      ref="notification"
      :message="notificationMessage"
      type="info"
      :okText="props.currentLang === 'en-US' ? 'OK' : '确定'"
    />
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from 'vue'
import Notification from './Notification.vue'
import { type AppLanguage, type AppTheme, getSettings, updateSettings } from '../lib/api'
import { ensureGuestUser } from '../lib/guestSession'
import { usePageSeo } from '../lib/usePageSeo'

const props = defineProps<{
  currentLang: AppLanguage
}>()

usePageSeo({
  title:
    props.currentLang === 'en-US'
      ? 'Settings | Parallel Worlds'
      : '设置 | Parallel Worlds',
  description:
    props.currentLang === 'en-US'
      ? 'Adjust language and theme preferences for the guest-mode open-source experience.'
      : '调整访客模式开源体验中的语言和主题偏好。',
  path: '/settings',
  noindex: true
})

const emit = defineEmits<{
  (e: 'language-change', language: AppLanguage): void
  (e: 'theme-change', theme: AppTheme): void
}>()

const currentTheme = ref<AppTheme>('system')
const notification = ref<InstanceType<typeof Notification>>()
const notificationMessage = ref('')

const translations = {
  'en-US': {
    eyebrow: 'Settings',
    title: 'Preferences',
    subtitle: 'Parallel Worlds stores a lightweight preference profile for your guest identity on your own server.',
    language: 'Language',
    theme: 'Theme',
    system: 'System',
    light: 'Light',
    dark: 'Dark',
    mode: 'Session mode',
    guestNotice: 'Guest mode is enabled in the open-source release. No email signup or cloud auth is required.',
    saved: 'Preferences saved.'
  },
  'zh-CN': {
    eyebrow: '设置',
    title: '偏好设置',
    subtitle: 'Parallel Worlds 会在你自己的服务器上为访客身份保存一份轻量级偏好配置。',
    language: '语言',
    theme: '主题',
    system: '跟随系统',
    light: '浅色',
    dark: '深色',
    mode: '会话模式',
    guestNotice: '开源版默认启用访客模式，不需要邮箱注册或云认证。',
    saved: '偏好已保存。'
  }
} as const

const t = (key: keyof typeof translations['en-US']) => translations[props.currentLang][key]

async function loadUserSettings() {
  const guestUserId = await ensureGuestUser()
  const settings = await getSettings(guestUserId)
  currentTheme.value = settings.theme
}

async function changeLanguage(language: AppLanguage) {
  const guestUserId = await ensureGuestUser()
  await updateSettings(guestUserId, { language })
  emit('language-change', language)
  notificationMessage.value = t('saved')
  notification.value?.show()
}

async function changeTheme(theme: AppTheme) {
  const guestUserId = await ensureGuestUser()
  await updateSettings(guestUserId, { theme })
  currentTheme.value = theme
  emit('theme-change', theme)
  notificationMessage.value = t('saved')
  notification.value?.show()
}

onMounted(async () => {
  try {
    await loadUserSettings()
  } catch (error) {
    console.error('Failed to load settings:', error)
  }
})
</script>

<style scoped>
.settings-container {
  min-height: 100vh;
  padding: 110px 20px 60px;
  font-family: monospace;
}

.settings-shell {
  width: min(820px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 28px;
}

.eyebrow {
  margin: 0 0 8px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.75rem;
  opacity: 0.7;
}

h1 {
  margin: 0 0 10px;
  font-size: clamp(2rem, 5vw, 3.1rem);
}

.subtitle {
  max-width: 60ch;
  line-height: 1.7;
  opacity: 0.82;
}

.panel {
  display: grid;
  gap: 20px;
  padding: 24px;
  border: 1px solid rgba(127, 127, 127, 0.28);
}

.setting-block label {
  display: block;
  margin-bottom: 10px;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.85rem;
  opacity: 0.7;
}

.option-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.option-button {
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  padding: 10px 14px;
  cursor: pointer;
  font-family: inherit;
}

.option-button.active {
  background: currentColor;
  color: var(--settings-bg, #fff);
}

.guest-note p {
  margin: 0;
  line-height: 1.7;
}

:global(.theme-light) {
  --settings-bg: #f5f0e7;
}

:global(.theme-dark) {
  --settings-bg: #111111;
}

@media (max-width: 720px) {
  .settings-container {
    padding-top: 92px;
  }

  .option-row {
    flex-direction: column;
  }

  .option-button {
    width: 100%;
  }
}
</style>
