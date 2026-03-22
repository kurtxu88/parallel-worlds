<template>
  <div class="world-building">
    <div class="building-container">
      <div v-if="loading" class="loading-block">
        <div class="loading-dots">
          <span>.</span>
          <span>.</span>
          <span>.</span>
        </div>
        <p>{{ t('checking') }}</p>
      </div>

      <div v-else-if="storyStatus === 'completed'" class="hidden-state"></div>

      <div v-else-if="storyStatus === 'failed' || storyStatus === 'error'" class="error-block">
        <div class="error-icon">x</div>
        <p>{{ t('failed') }}</p>
        <button class="retry-button" @click="handleRetry" :disabled="retrying">
          {{ retrying ? t('retrying') : t('retry') }}
        </button>
      </div>

      <div v-else class="loading-block">
        <div class="loading-dots">
          <span>.</span>
          <span>.</span>
          <span>.</span>
        </div>
        <p>{{ t('building') }}</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import { type AppLanguage, getStory, retryStory } from '../lib/api'
import { ensureGuestUser } from '../lib/guestSession'

const props = defineProps<{
  currentLang: AppLanguage
}>()

const emit = defineEmits<{
  (e: 'story-completed'): void
}>()

const route = useRoute()
const loading = ref(true)
const storyStatus = ref<'pending' | 'generating' | 'completed' | 'failed' | 'error'>('pending')
const retrying = ref(false)

let pollIntervalId: number | null = null

const translations = {
  'en-US': {
    checking: 'Checking world status...',
    building: 'Your world is being generated. This can take several minutes.',
    failed: 'World generation failed.',
    retry: 'Retry generation',
    retrying: 'Retrying...'
  },
  'zh-CN': {
    checking: '正在检查世界状态...',
    building: '你的世界正在生成，这可能需要几分钟。',
    failed: '世界生成失败。',
    retry: '重新生成',
    retrying: '重试中...'
  }
} as const

const t = (key: keyof typeof translations['en-US']) => translations[props.currentLang][key]

async function checkStoryStatus() {
  const storyId = String(route.params.id || '')
  if (!storyId) {
    loading.value = false
    return
  }

  try {
    const guestUserId = await ensureGuestUser()
    const story = await getStory(guestUserId, storyId)
    storyStatus.value = story.status

    if (story.status === 'completed') {
      stopPolling()
      emit('story-completed')
    }
  } catch (error) {
    console.error('Failed to check story status:', error)
  } finally {
    loading.value = false
  }
}

async function handleRetry() {
  const storyId = String(route.params.id || '')
  if (!storyId) {
    return
  }

  retrying.value = true

  try {
    const guestUserId = await ensureGuestUser()
    const story = await retryStory(guestUserId, storyId)
    storyStatus.value = story.status
    loading.value = false
    startPolling()
  } catch (error) {
    console.error('Failed to retry story:', error)
  } finally {
    retrying.value = false
  }
}

function startPolling() {
  stopPolling()
  pollIntervalId = window.setInterval(async () => {
    if (!['pending', 'generating'].includes(storyStatus.value)) {
      return
    }
    await checkStoryStatus()
  }, 5000)
}

function stopPolling() {
  if (pollIntervalId !== null) {
    window.clearInterval(pollIntervalId)
    pollIntervalId = null
  }
}

onMounted(async () => {
  await checkStoryStatus()
  startPolling()
})

onUnmounted(() => {
  stopPolling()
})
</script>

<style scoped>
.world-building {
  position: fixed;
  inset: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  padding-top: 90px;
  background: rgba(13, 13, 13, 0.7);
  backdrop-filter: blur(10px);
  z-index: 50;
  font-family: monospace;
}

.building-container {
  width: min(420px, calc(100% - 32px));
  padding: 28px;
  text-align: center;
  border: 1px solid rgba(255, 255, 255, 0.2);
  background: rgba(16, 16, 16, 0.82);
  color: #f2ede3;
}

.loading-block,
.error-block {
  display: grid;
  gap: 16px;
}

.loading-dots {
  font-size: 2rem;
  letter-spacing: 0.35em;
}

.loading-dots span {
  animation: pulse 1.2s infinite ease-in-out;
}

.loading-dots span:nth-child(2) {
  animation-delay: 0.15s;
}

.loading-dots span:nth-child(3) {
  animation-delay: 0.3s;
}

.retry-button {
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  padding: 10px 14px;
  cursor: pointer;
  font-family: inherit;
}

.hidden-state {
  display: none;
}

.error-icon {
  font-size: 1.75rem;
}

@keyframes pulse {
  0%,
  100% {
    opacity: 0.3;
    transform: translateY(0);
  }
  50% {
    opacity: 1;
    transform: translateY(-4px);
  }
}
</style>
