<template>
  <main class="public-discovery-page">
    <div class="page-shell">
      <section class="hero">
        <div class="hero-copy">
          <p class="eyebrow">{{ t('eyebrow') }}</p>
          <h1>{{ t('title') }}</h1>
          <p class="subtitle">{{ t('subtitle') }}</p>

          <div class="hero-actions">
            <router-link class="primary-link" :to="{ name: 'create' }">
              {{ t('createAction') }}
            </router-link>
            <router-link class="secondary-link" :to="{ name: 'landing' }">
              {{ t('homeAction') }}
            </router-link>
            <button class="secondary-link" type="button" @click="loadStories">
              {{ t('reloadAction') }}
            </button>
          </div>
        </div>

        <aside class="hero-panel">
          <div class="language-row">
            <button
              class="lang-button"
              :class="{ active: currentLang === 'en-US' }"
              @click="emit('language-change', 'en-US')"
            >
              English
            </button>
            <button
              class="lang-button"
              :class="{ active: currentLang === 'zh-CN' }"
              @click="emit('language-change', 'zh-CN')"
            >
              中文
            </button>
          </div>

          <div class="stats-grid">
            <article class="stat-card">
              <p class="stat-label">{{ t('publicWorlds') }}</p>
              <p class="stat-value">{{ stories.length }}</p>
            </article>
            <article class="stat-card">
              <p class="stat-label">{{ t('totalEvents') }}</p>
              <p class="stat-value">{{ totalEvents }}</p>
            </article>
          </div>

          <p class="hero-note">{{ summaryCopy }}</p>
        </aside>
      </section>

      <div v-if="errorMessage" class="notice error">
        {{ errorMessage }}
      </div>

      <section v-else-if="isLoading" class="empty-panel">
        <p class="empty-title">{{ t('loading') }}</p>
      </section>

      <section v-else-if="stories.length === 0" class="empty-panel">
        <p class="empty-title">{{ t('emptyTitle') }}</p>
        <p class="empty-copy">{{ t('emptyBody') }}</p>
        <div class="hero-actions">
          <router-link class="primary-link" :to="{ name: 'create' }">
            {{ t('emptyAction') }}
          </router-link>
          <router-link class="secondary-link" :to="{ name: 'worlds' }">
            {{ t('emptyManageAction') }}
          </router-link>
        </div>
      </section>

      <section v-else class="story-grid">
        <article v-for="story in stories" :key="story.id" class="story-card">
          <div class="card-head">
            <span class="pill">{{ formatLanguage(story.culture_language) }}</span>
            <span class="pill status" :class="story.status">{{ formatStatus(story.status) }}</span>
          </div>

          <h2>{{ getStoryTitle(story) }}</h2>
          <p class="seed-label">{{ t('seedLabel') }}</p>
          <p class="seed-copy">{{ story.user_input }}</p>

          <p class="preview-label">{{ t('previewLabel') }}</p>
          <p class="preview-copy">{{ getPreviewText(story) }}</p>

          <div class="meta-grid">
            <div class="meta-item">
              <p class="meta-label">{{ t('updated') }}</p>
              <p class="meta-value">{{ formatDate(story.last_entered_at || story.updated_at) }}</p>
            </div>
            <div class="meta-item">
              <p class="meta-label">{{ t('events') }}</p>
              <p class="meta-value">{{ formatEventCount(story.event_count) }}</p>
            </div>
          </div>

          <div class="card-actions">
            <router-link class="primary-link" :to="{ name: 'share', params: { id: story.id } }">
              {{ t('openStory') }}
            </router-link>
            <router-link class="secondary-link" :to="getStoryRemixPath(story)">
              {{ t('remixAction') }}
            </router-link>
          </div>
        </article>
      </section>
    </div>
  </main>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { AppLanguage, PublicStorySummary } from '../lib/api'
import { getPublicStories } from '../lib/api'
import { getStoryRemixPath } from '../lib/storyLinks'
import { usePageSeo } from '../lib/usePageSeo'

const props = defineProps<{
  currentLang: AppLanguage
}>()

const emit = defineEmits<{
  (e: 'language-change', language: AppLanguage): void
}>()

const stories = ref<PublicStorySummary[]>([])
const isLoading = ref(true)
const errorMessage = ref('')

const translations = {
  'en-US': {
    eyebrow: 'Public world discovery',
    title: 'Browse the worlds people decided were worth sharing.',
    subtitle:
      'This feed turns individual share pages into a browsable showcase, so new visitors can quickly understand what Parallel Worlds can produce.',
    createAction: 'Create a world',
    homeAction: 'Project home',
    reloadAction: 'Refresh feed',
    publicWorlds: 'Public worlds',
    totalEvents: 'Transcript events',
    loading: 'Loading public worlds...',
    emptyTitle: 'No public worlds have been shared yet.',
    emptyBody:
      'Create a world, turn on sharing, and it will start the public gallery for future visitors.',
    emptyAction: 'Publish the first world',
    emptyManageAction: 'Open my worlds',
    loadFailed: 'Failed to load the public discovery feed.',
    seedLabel: 'Story seed',
    previewLabel: 'Latest playable moment',
    updated: 'Last activity',
    events: 'Transcript size',
    openStory: 'Read world',
    remixAction: 'Remix',
    fallbackTitle: 'Untitled public world',
    previewFallback:
      'This world is public, but it does not have a visible transcript excerpt yet.',
    pending: 'Queued',
    generating: 'Generating',
    completed: 'Ready',
    failed: 'Failed',
    error: 'Error',
    summaryZero: 'Share pages are live. The discovery feed is ready for the first published world.',
    summaryOne: '1 public world is live and ready to be shared in posts, demos, and README links.',
    summaryMany:
      '{count} public worlds are live. This page is now a better entry point for curious visitors than a raw repo alone.',
    languageEnglish: 'English',
    languageChinese: '中文'
  },
  'zh-CN': {
    eyebrow: '公开世界发现页',
    title: '浏览那些被作者主动公开出来、值得分享的世界。',
    subtitle:
      '这个页面把原本分散的单个分享页串成了一个可浏览的展示层，让新访客更快理解 Parallel Worlds 到底能生成什么。',
    createAction: '创建世界',
    homeAction: '返回项目首页',
    reloadAction: '刷新列表',
    publicWorlds: '公开世界数',
    totalEvents: '互动记录数',
    loading: '正在加载公开世界...',
    emptyTitle: '还没有公开分享的世界。',
    emptyBody:
      '先创建一个世界并开启公开分享，这里就会成为后续访客可直接浏览的展示页。',
    emptyAction: '发布第一个世界',
    emptyManageAction: '打开我的世界',
    loadFailed: '加载公开发现页失败。',
    seedLabel: '世界种子',
    previewLabel: '最近一次可游玩片段',
    updated: '最近活动',
    events: '互动记录',
    openStory: '阅读世界',
    remixAction: '基于它继续创作',
    fallbackTitle: '未命名公开世界',
    previewFallback: '这个世界已经公开，但还没有可展示的互动片段。',
    pending: '排队中',
    generating: '生成中',
    completed: '可进入',
    failed: '生成失败',
    error: '错误',
    summaryZero: '分享页已经准备好了，发现页只差第一个公开世界。',
    summaryOne: '现在已经有 1 个公开世界，可以直接拿去做帖子、demo 和 README 链接。',
    summaryMany:
      '现在已经有 {count} 个公开世界，这个页面已经比单纯看仓库更适合作为新访客入口。',
    languageEnglish: 'English',
    languageChinese: '中文'
  }
} as const

const t = (key: keyof typeof translations['en-US']) => translations[props.currentLang][key]

usePageSeo({
  title:
    props.currentLang === 'en-US'
      ? 'Discover Public Worlds | Parallel Worlds'
      : '发现公开世界 | Parallel Worlds',
  description:
    props.currentLang === 'en-US'
      ? 'Browse public Parallel Worlds stories, read shared worlds, and remix them into your own playable sessions.'
      : '浏览公开的 Parallel Worlds 世界，阅读分享故事，并基于它继续创作你自己的可游玩会话。',
  path: '/discover'
})

const totalEvents = computed(() =>
  stories.value.reduce((sum, story) => sum + Number(story.event_count || 0), 0)
)

const summaryCopy = computed(() => {
  const count = stories.value.length

  if (count === 0) {
    return t('summaryZero')
  }

  if (count === 1) {
    return t('summaryOne')
  }

  return t('summaryMany').replace('{count}', String(count))
})

function formatDate(value: string) {
  return new Intl.DateTimeFormat(props.currentLang, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function formatStatus(status: PublicStorySummary['status']) {
  return t(status)
}

function formatEventCount(count: number) {
  if (props.currentLang === 'zh-CN') {
    return `${count} 条`
  }

  return `${count} events`
}

function formatLanguage(language: AppLanguage) {
  return language === 'zh-CN' ? t('languageChinese') : t('languageEnglish')
}

function getStoryTitle(story: PublicStorySummary) {
  return story.story_title || story.user_input || t('fallbackTitle')
}

function getPreviewText(story: PublicStorySummary) {
  const content = (story.preview_excerpt || '').trim()

  if (!content) {
    return t('previewFallback')
  }

  if (content.length <= 220) {
    return content
  }

  return `${content.slice(0, 217)}...`
}

async function loadStories() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    stories.value = await getPublicStories(24)
  } catch {
    errorMessage.value = t('loadFailed')
  } finally {
    isLoading.value = false
  }
}

onMounted(loadStories)
</script>

<style scoped>
.public-discovery-page {
  min-height: 100vh;
  padding: 120px 20px 64px;
  font-family: monospace;
  background:
    radial-gradient(circle at top left, rgba(13, 148, 136, 0.16), transparent 30%),
    radial-gradient(circle at bottom right, rgba(217, 119, 6, 0.16), transparent 28%);
}

.page-shell {
  width: min(1180px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 24px;
}

.hero,
.hero-panel,
.story-card,
.empty-panel,
.notice,
.stat-card {
  border: 1px solid rgba(127, 127, 127, 0.28);
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(8px);
}

.hero {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(300px, 0.9fr);
  gap: 18px;
  background: transparent;
  border: 0;
}

.hero-copy,
.hero-panel,
.story-card,
.empty-panel,
.notice {
  padding: 28px;
}

.eyebrow,
.stat-label,
.seed-label,
.preview-label,
.meta-label {
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.74rem;
  opacity: 0.7;
}

h1 {
  margin: 0 0 16px;
  font-size: clamp(2.4rem, 6vw, 4.8rem);
  line-height: 1;
}

h2 {
  margin: 0 0 18px;
  font-size: 1.5rem;
  line-height: 1.2;
}

.subtitle,
.hero-note,
.seed-copy,
.preview-copy,
.empty-copy {
  line-height: 1.7;
}

.hero-actions,
.language-row,
.card-actions,
.card-head,
.meta-grid,
.stats-grid {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.hero-actions,
.language-row,
.card-actions {
  margin-top: 22px;
}

.stats-grid {
  margin-top: 18px;
}

.primary-link,
.secondary-link,
.lang-button {
  border: 1px solid currentColor;
  color: inherit;
  text-decoration: none;
  padding: 12px 16px;
  font-family: inherit;
  background: transparent;
  cursor: pointer;
}

.primary-link,
.lang-button.active {
  background: currentColor;
  color: var(--discovery-bg, #ffffff);
}

.stat-card {
  padding: 16px;
  min-width: 150px;
}

.stat-label,
.meta-label {
  margin-bottom: 6px;
}

.stat-value,
.meta-value {
  margin: 0;
  font-size: 1.1rem;
}

.story-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.story-card {
  display: grid;
  gap: 16px;
}

.card-head {
  margin-top: 0;
}

.pill {
  display: inline-flex;
  align-items: center;
  padding: 6px 10px;
  border: 1px solid currentColor;
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
}

.pill.status.completed {
  background: rgba(21, 128, 61, 0.12);
}

.pill.status.generating,
.pill.status.pending {
  background: rgba(217, 119, 6, 0.12);
}

.pill.status.failed,
.pill.status.error {
  background: rgba(220, 38, 38, 0.12);
}

.seed-copy,
.preview-copy {
  margin: 0;
}

.preview-copy {
  min-height: 88px;
}

.meta-grid {
  margin-top: auto;
}

.meta-item {
  flex: 1 1 160px;
}

.empty-panel,
.notice {
  text-align: left;
}

.empty-title {
  margin: 0 0 10px;
  font-size: 1.4rem;
}

:global(.theme-light) {
  --discovery-bg: #f5f0e7;
}

:global(.theme-dark) {
  --discovery-bg: #111111;
}

@media (max-width: 980px) {
  .hero,
  .story-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .public-discovery-page {
    padding-top: 92px;
  }

  .hero-copy,
  .hero-panel,
  .story-card,
  .empty-panel,
  .notice {
    padding: 22px;
  }

  .stat-card {
    width: 100%;
  }
}
</style>
