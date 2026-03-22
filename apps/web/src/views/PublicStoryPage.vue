<template>
  <section class="public-story-page">
    <div class="page-shell">
      <header class="hero">
        <p class="eyebrow">{{ t('eyebrow') }}</p>
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
        <h1>{{ titleText }}</h1>
        <p class="subtitle">{{ story?.user_input || t('subtitle') }}</p>

        <div class="action-row">
          <router-link v-if="story" class="primary-link" :to="getStoryRemixPath(story)">
            {{ t('remixAction') }}
          </router-link>
          <router-link class="secondary-link" :to="getPublicDiscoveryPath()">
            {{ t('discoverAction') }}
          </router-link>
          <router-link class="secondary-link" :to="{ name: 'landing' }">
            {{ t('homeAction') }}
          </router-link>
        </div>
      </header>

      <div v-if="errorMessage" class="notice error">
        {{ errorMessage }}
      </div>

      <div v-else-if="isLoading" class="empty-panel">
        {{ t('loading') }}
      </div>

      <template v-else-if="story">
        <section class="meta-grid">
          <article class="meta-card">
            <p class="meta-label">{{ t('status') }}</p>
            <p class="meta-value">{{ formatStatus(story.status) }}</p>
          </article>
          <article class="meta-card">
            <p class="meta-label">{{ t('createdAt') }}</p>
            <p class="meta-value">{{ formatDate(story.created_at) }}</p>
          </article>
          <article class="meta-card">
            <p class="meta-label">{{ t('lastUpdated') }}</p>
            <p class="meta-value">{{ formatDate(story.updated_at) }}</p>
          </article>
        </section>

        <section v-if="displayEvents.length > 0" class="transcript">
          <article
            v-for="event in displayEvents"
            :key="event.id"
            class="transcript-entry"
            :class="event.event_type"
          >
            <p class="entry-label">
              {{ event.event_type === 'user_input' ? t('playerLabel') : t('worldLabel') }}
            </p>
            <p class="entry-content">{{ event.content }}</p>
          </article>
        </section>

        <section v-else class="empty-panel">
          {{ emptyStateCopy }}
        </section>
      </template>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import type { AppLanguage, PublicStoryEvent, PublicStoryRecord } from '../lib/api'
import { getPublicStory, getPublicStoryEvents } from '../lib/api'
import { getPublicDiscoveryPath, getStoryRemixPath } from '../lib/storyLinks'
import { usePageSeo } from '../lib/usePageSeo'

const props = defineProps<{
  storyId: string
  currentLang: AppLanguage
}>()

const emit = defineEmits<{
  (e: 'language-change', language: AppLanguage): void
}>()

const story = ref<PublicStoryRecord | null>(null)
const events = ref<PublicStoryEvent[]>([])
const isLoading = ref(true)
const errorMessage = ref('')

const translations = {
  'en-US': {
    eyebrow: 'Public world',
    subtitle: 'A shared Parallel Worlds session you can read, remix, and explore.',
    remixAction: 'Remix this world',
    discoverAction: 'Browse public worlds',
    homeAction: 'Project home',
    loading: 'Loading the public world...',
    status: 'Status',
    createdAt: 'Created',
    lastUpdated: 'Last updated',
    playerLabel: 'Player',
    worldLabel: 'World',
    pending: 'Queued',
    generating: 'Generating',
    completed: 'Ready',
    failed: 'Failed',
    error: 'Error',
    noTranscriptReady: 'This world is public, but the playable transcript is not ready yet.',
    noTranscriptFailed: 'This shared world hit an error before a transcript was produced.',
    storyMissing: 'This public world could not be found.',
    loadFailed: 'Failed to load this public world.'
  },
  'zh-CN': {
    eyebrow: '公开世界',
    subtitle: '这是一个可阅读、可二次创作、可继续探索的 Parallel Worlds 分享页面。',
    remixAction: '基于它重新创作',
    discoverAction: '浏览公开世界',
    homeAction: '返回项目首页',
    loading: '正在加载公开世界...',
    status: '当前状态',
    createdAt: '创建时间',
    lastUpdated: '最近更新',
    playerLabel: '玩家',
    worldLabel: '世界',
    pending: '排队中',
    generating: '生成中',
    completed: '可进入',
    failed: '生成失败',
    error: '错误',
    noTranscriptReady: '这个世界已经公开，但可阅读的互动记录还没有准备好。',
    noTranscriptFailed: '这个分享世界在生成过程中出错，因此还没有可展示的互动记录。',
    storyMissing: '找不到这个公开世界。',
    loadFailed: '加载这个公开世界失败。'
  }
} as const

const t = (key: keyof typeof translations['en-US']) => translations[props.currentLang][key]

usePageSeo({
  title:
    props.currentLang === 'en-US'
      ? 'Shared World | Parallel Worlds'
      : '共享世界 | Parallel Worlds',
  description:
    props.currentLang === 'en-US'
      ? 'Explore a public Parallel Worlds story and remix it into your own playable world.'
      : '浏览一个公开的 Parallel Worlds 世界，并基于它继续创作你自己的可游玩故事。',
  path: `/share/${props.storyId}`
})

const titleText = computed(() => {
  if (!story.value) {
    return props.currentLang === 'en-US' ? 'Shared Parallel World' : '共享平行世界'
  }

  return story.value.story_title || story.value.user_input
})

const displayEvents = computed(() =>
  events.value.filter(event => event.event_type === 'user_input' || event.event_type === 'ai_response')
)

const emptyStateCopy = computed(() => {
  if (!story.value) {
    return ''
  }

  if (story.value.status === 'failed' || story.value.status === 'error') {
    return t('noTranscriptFailed')
  }

  return t('noTranscriptReady')
})

function formatDate(value: string) {
  return new Intl.DateTimeFormat(props.currentLang, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function formatStatus(status: PublicStoryRecord['status']) {
  return t(status)
}

onMounted(async () => {
  try {
    const [publicStory, publicEvents] = await Promise.all([
      getPublicStory(props.storyId),
      getPublicStoryEvents(props.storyId)
    ])

    story.value = publicStory
    events.value = publicEvents
  } catch (error) {
    if (error instanceof Error) {
      errorMessage.value =
        error.message === 'Public story not found' ? t('storyMissing') : t('loadFailed')
    } else {
      errorMessage.value = t('loadFailed')
    }
  } finally {
    isLoading.value = false
  }
})
</script>

<style scoped>
.public-story-page {
  min-height: 100vh;
  padding: 120px 20px 60px;
  font-family: monospace;
}

.page-shell {
  width: min(960px, 100%);
  margin: 0 auto;
  display: grid;
  gap: 28px;
}

.hero,
.meta-card,
.transcript-entry,
.empty-panel {
  border: 1px solid rgba(127, 127, 127, 0.28);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent),
    radial-gradient(circle at top left, rgba(244, 178, 110, 0.08), transparent 30%);
}

.hero {
  padding: 30px;
}

.language-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.lang-button {
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  padding: 10px 12px;
  cursor: pointer;
  font: inherit;
}

.lang-button.active {
  background: currentColor;
  color: var(--public-story-bg, #fff);
}

.eyebrow,
.meta-label,
.entry-label {
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.16em;
  font-size: 0.76rem;
  opacity: 0.68;
}

h1 {
  margin: 0 0 12px;
  font-size: clamp(2.2rem, 6vw, 4rem);
  line-height: 1;
}

.subtitle,
.entry-content,
.empty-panel {
  line-height: 1.75;
}

.action-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 24px;
}

.primary-link,
.secondary-link {
  border: 1px solid currentColor;
  color: inherit;
  text-decoration: none;
  padding: 12px 16px;
}

.primary-link {
  background: currentColor;
  color: var(--public-story-bg, #fff);
}

.notice {
  padding: 14px 16px;
  border: 1px solid currentColor;
}

.notice.error {
  color: #b42318;
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.meta-card,
.empty-panel {
  padding: 22px;
}

.meta-value {
  margin: 0;
  font-size: 1.05rem;
}

.transcript {
  display: grid;
  gap: 14px;
}

.transcript-entry {
  padding: 22px;
}

.transcript-entry.user_input {
  border-color: rgba(244, 178, 110, 0.4);
}

.transcript-entry.ai_response {
  border-color: rgba(14, 116, 144, 0.35);
}

.entry-content {
  margin: 0;
  white-space: pre-wrap;
}

:global(.theme-light) {
  --public-story-bg: #f5f0e7;
}

:global(.theme-dark) {
  --public-story-bg: #111111;
}

@media (max-width: 760px) {
  .public-story-page {
    padding-top: 96px;
  }

  .meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>
