<template>
  <section class="stories-list">
    <header class="page-header">
      <div>
        <p class="eyebrow">{{ t('eyebrow') }}</p>
        <h1>{{ t('title') }}</h1>
        <p class="page-copy">{{ t('subtitle') }}</p>
      </div>
      <div class="header-actions">
        <button class="secondary-button" @click="loadStories" :disabled="isLoading">
          {{ isLoading ? t('refreshing') : t('refresh') }}
        </button>
        <button class="primary-button" @click="emit('navigate', 'create')">
          {{ t('createWorld') }}
        </button>
      </div>
    </header>

    <div v-if="errorMessage" class="notice error">
      {{ errorMessage }}
    </div>

    <div v-if="isLoading" class="empty-state">
      <p>{{ t('loading') }}</p>
    </div>

    <div v-else-if="stories.length === 0" class="empty-state">
      <p>{{ t('emptyTitle') }}</p>
      <button class="primary-button" @click="emit('navigate', 'create')">
        {{ t('createFirst') }}
      </button>
    </div>

    <div v-else class="stories-grid">
      <article
        v-for="story in stories"
        :key="story.id"
        class="story-card"
        @click="emit('view-story', story)"
      >
        <div class="story-card-header">
          <div>
            <p class="story-kicker">{{ t('worldLabel') }}</p>
            <h2>{{ story.story_title || getFallbackTitle(story) }}</h2>
          </div>
          <span class="status-pill" :class="story.status">
            {{ formatStatus(story.status) }}
          </span>
        </div>

        <p class="story-description">{{ story.user_input }}</p>

        <dl class="story-meta">
          <div>
            <dt>{{ t('createdAt') }}</dt>
            <dd>{{ formatDate(story.created_at) }}</dd>
          </div>
          <div>
            <dt>{{ t('lastPlayed') }}</dt>
            <dd>{{ story.last_entered_at ? formatDate(story.last_entered_at) : t('neverPlayed') }}</dd>
          </div>
        </dl>

        <p v-if="story.error_message" class="error-copy">
          {{ story.error_message }}
        </p>
      </article>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { type AppLanguage, type StoryRecord, getStories } from '../lib/api'
import { ensureGuestUser } from '../lib/guestSession'

const props = defineProps<{
  currentLang: AppLanguage
}>()

const emit = defineEmits<{
  (e: 'view-story', story: StoryRecord): void
  (e: 'navigate', view: string): void
}>()

const stories = ref<StoryRecord[]>([])
const isLoading = ref(true)
const errorMessage = ref('')

let pollIntervalId: number | null = null

const translations = {
  'en-US': {
    eyebrow: 'Library',
    title: 'Your parallel worlds',
    subtitle: 'Every world seed you create stays here, together with its latest progress and play history.',
    loading: 'Loading your worlds...',
    emptyTitle: 'No worlds yet.',
    createFirst: 'Create the first one',
    createWorld: 'Create world',
    refresh: 'Refresh',
    refreshing: 'Refreshing...',
    worldLabel: 'WORLD',
    createdAt: 'Created',
    lastPlayed: 'Last played',
    neverPlayed: 'Not played yet',
    pending: 'Queued',
    generating: 'Generating',
    completed: 'Ready',
    failed: 'Failed',
    error: 'Error'
  },
  'zh-CN': {
    eyebrow: '世界库',
    title: '你的平行世界',
    subtitle: '你创建的每个世界种子都会保存在这里，并显示最新生成进度和游玩历史。',
    loading: '正在加载你的世界...',
    emptyTitle: '还没有世界。',
    createFirst: '创建第一个世界',
    createWorld: '创建世界',
    refresh: '刷新',
    refreshing: '刷新中...',
    worldLabel: '世界',
    createdAt: '创建时间',
    lastPlayed: '最近游玩',
    neverPlayed: '尚未游玩',
    pending: '排队中',
    generating: '生成中',
    completed: '可进入',
    failed: '生成失败',
    error: '错误'
  }
} as const

const t = (key: keyof typeof translations['en-US']) => translations[props.currentLang][key]

function formatStatus(status: StoryRecord['status']) {
  return t(status)
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(props.currentLang, {
    dateStyle: 'medium',
    timeStyle: 'short'
  }).format(new Date(value))
}

function getFallbackTitle(story: StoryRecord) {
  const trimmed = story.user_input.trim()
  if (!trimmed) {
    return props.currentLang === 'en-US' ? 'Untitled world' : '未命名世界'
  }

  return trimmed.length > 48 ? `${trimmed.slice(0, 48)}...` : trimmed
}

async function loadStories() {
  isLoading.value = true
  errorMessage.value = ''

  try {
    const guestUserId = await ensureGuestUser()
    stories.value = await getStories(guestUserId)
  } catch (error) {
    errorMessage.value =
      error instanceof Error
        ? error.message
        : props.currentLang === 'en-US'
          ? 'Failed to load stories.'
          : '加载世界失败。'
  } finally {
    isLoading.value = false
  }
}

function startPolling() {
  stopPolling()
  pollIntervalId = window.setInterval(async () => {
    const hasActiveStory = stories.value.some(story => ['pending', 'generating'].includes(story.status))
    if (!hasActiveStory) {
      return
    }
    await loadStories()
  }, 5000)
}

function stopPolling() {
  if (pollIntervalId !== null) {
    window.clearInterval(pollIntervalId)
    pollIntervalId = null
  }
}

onMounted(async () => {
  await loadStories()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.stories-list {
  width: min(1080px, 100%);
  margin: 0 auto;
  padding: 120px 20px 60px;
  font-family: monospace;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 24px;
  align-items: end;
  margin-bottom: 32px;
}

.eyebrow {
  margin: 0 0 8px;
  letter-spacing: 0.18em;
  text-transform: uppercase;
  font-size: 0.75rem;
  opacity: 0.7;
}

h1 {
  margin: 0;
  font-size: clamp(2rem, 5vw, 3.2rem);
}

.page-copy {
  max-width: 58ch;
  line-height: 1.6;
  opacity: 0.8;
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.primary-button,
.secondary-button {
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  padding: 12px 18px;
  cursor: pointer;
  font-family: inherit;
}

.primary-button {
  background: currentColor;
  color: var(--page-bg, #fff);
}

.notice {
  margin-bottom: 20px;
  padding: 14px 16px;
  border: 1px solid currentColor;
}

.notice.error {
  color: #b42318;
}

.empty-state {
  min-height: 260px;
  display: grid;
  place-items: center;
  gap: 16px;
  text-align: center;
  border: 1px dashed rgba(127, 127, 127, 0.35);
}

.stories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 20px;
}

.story-card {
  padding: 20px;
  border: 1px solid rgba(127, 127, 127, 0.3);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent),
    radial-gradient(circle at top right, rgba(255, 255, 255, 0.1), transparent 35%);
  cursor: pointer;
  transition: transform 0.18s ease, border-color 0.18s ease;
}

.story-card:hover {
  transform: translateY(-2px);
  border-color: rgba(127, 127, 127, 0.6);
}

.story-card-header {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.story-kicker {
  margin: 0 0 4px;
  font-size: 0.75rem;
  opacity: 0.6;
  letter-spacing: 0.12em;
}

.story-card h2 {
  margin: 0;
  font-size: 1.05rem;
  line-height: 1.4;
}

.status-pill {
  align-self: start;
  padding: 6px 10px;
  border: 1px solid currentColor;
  font-size: 0.75rem;
  white-space: nowrap;
}

.status-pill.pending,
.status-pill.generating {
  color: #9a6700;
}

.status-pill.completed {
  color: #0f766e;
}

.status-pill.failed,
.status-pill.error {
  color: #b42318;
}

.story-description {
  min-height: 96px;
  margin: 0 0 18px;
  line-height: 1.6;
  white-space: pre-wrap;
}

.story-meta {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  margin: 0;
}

.story-meta dt {
  font-size: 0.75rem;
  opacity: 0.65;
  margin-bottom: 4px;
}

.story-meta dd {
  margin: 0;
}

.error-copy {
  margin: 18px 0 0;
  color: #b42318;
  line-height: 1.5;
}

:global(.theme-light) {
  --page-bg: #f5f0e7;
}

:global(.theme-dark) {
  --page-bg: #111111;
}

@media (max-width: 720px) {
  .stories-list {
    padding-top: 96px;
  }

  .page-header {
    flex-direction: column;
    align-items: start;
  }

  .header-actions {
    width: 100%;
  }

  .primary-button,
  .secondary-button {
    flex: 1;
  }
}
</style>
