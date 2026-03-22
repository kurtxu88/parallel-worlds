<template>
  <section class="story-creator">
    <div class="creator-shell">
      <div class="intro-block">
        <p class="eyebrow">{{ t('eyebrow') }}</p>
        <h1>{{ t('title') }}</h1>
        <p class="subtitle">{{ t('subtitle') }}</p>
      </div>

      <div class="panel">
        <div class="field-group">
          <p class="field-label">{{ t('identityLabel') }}</p>
          <div class="choice-row">
            <button
              class="choice-button"
              :class="{ active: genderPreference === 'male' }"
              @click="genderPreference = 'male'"
            >
              {{ t('male') }}
            </button>
            <button
              class="choice-button"
              :class="{ active: genderPreference === 'female' }"
              @click="genderPreference = 'female'"
            >
              {{ t('female') }}
            </button>
          </div>
        </div>

        <div class="field-group">
          <label class="field-label" for="story-seed">{{ t('promptLabel') }}</label>
          <textarea
            id="story-seed"
            v-model="storyInput"
            class="story-input"
            :placeholder="t('placeholder')"
            rows="10"
          />
        </div>

        <div v-if="hasPendingStory" class="notice">
          {{ t('pendingNotice') }}
        </div>

        <div v-if="errorMessage" class="notice error">
          {{ errorMessage }}
        </div>

        <div class="action-row">
          <button class="secondary-button" @click="emit('navigate', 'worlds')">
            {{ t('backToWorlds') }}
          </button>
          <button
            class="primary-button"
            @click="handleSubmit"
            :disabled="isSubmitting || !storyInput.trim() || hasPendingStory"
          >
            {{ isSubmitting ? t('creating') : t('createAction') }}
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { type AppLanguage, createStory, getStories, type StoryRecord } from '../lib/api'
import { ensureGuestUser } from '../lib/guestSession'

const props = defineProps<{
  currentLang: AppLanguage
}>()

const emit = defineEmits<{
  (e: 'story-created', story: StoryRecord): void
  (e: 'navigate', view: string): void
}>()

const storyInput = ref('')
const genderPreference = ref<'male' | 'female'>('male')
const isSubmitting = ref(false)
const errorMessage = ref('')
const existingStories = ref<StoryRecord[]>([])

const translations = {
  'en-US': {
    eyebrow: 'Create',
    title: 'Seed a new world',
    subtitle: 'Describe the kind of life, conflict, and atmosphere you want the generator to build around you.',
    identityLabel: 'Who are you in this world?',
    promptLabel: 'World seed',
    male: 'Male',
    female: 'Female',
    placeholder: 'A disgraced court astronomer discovers that the moon above the capital is an artificial machine...',
    createAction: 'Create world',
    creating: 'Creating...',
    backToWorlds: 'Back to worlds',
    pendingNotice: 'You already have a world generating. Wait for it to finish before starting another.',
    createFailed: 'Failed to create the world.'
  },
  'zh-CN': {
    eyebrow: '创建',
    title: '播下一个新世界',
    subtitle: '描述你想进入的人生、冲突和氛围，让生成器围绕这些元素搭建完整世界。',
    identityLabel: '你在这个世界中是谁？',
    promptLabel: '世界种子',
    male: '男',
    female: '女',
    placeholder: '一位失宠的宫廷天文学家发现，王都上空的月亮其实是一台人工机器......',
    createAction: '创建世界',
    creating: '创建中...',
    backToWorlds: '返回世界列表',
    pendingNotice: '你已有一个世界正在生成，请等待它完成后再创建新的世界。',
    createFailed: '创建世界失败。'
  }
} as const

const t = (key: keyof typeof translations['en-US']) => translations[props.currentLang][key]

const hasPendingStory = computed(() =>
  existingStories.value.some(story => ['pending', 'generating'].includes(story.status))
)

async function refreshStories() {
  const guestUserId = await ensureGuestUser()
  existingStories.value = await getStories(guestUserId)
}

async function handleSubmit() {
  if (!storyInput.value.trim() || hasPendingStory.value) {
    return
  }

  isSubmitting.value = true
  errorMessage.value = ''

  try {
    const guestUserId = await ensureGuestUser()
    const story = await createStory(guestUserId, {
      user_input: storyInput.value.trim(),
      gender_preference: genderPreference.value,
      culture_language: props.currentLang
    })
    emit('story-created', story)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('createFailed')
  } finally {
    isSubmitting.value = false
  }
}

onMounted(async () => {
  try {
    await refreshStories()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('createFailed')
  }
})
</script>

<style scoped>
.story-creator {
  min-height: 100vh;
  padding: 110px 20px 60px;
  font-family: monospace;
}

.creator-shell {
  width: min(920px, 100%);
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
  font-size: clamp(2.1rem, 5vw, 3.4rem);
}

.subtitle {
  max-width: 60ch;
  line-height: 1.7;
  opacity: 0.82;
}

.panel {
  border: 1px solid rgba(127, 127, 127, 0.28);
  padding: 24px;
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.04), transparent),
    radial-gradient(circle at top left, rgba(255, 255, 255, 0.08), transparent 30%);
}

.field-group + .field-group {
  margin-top: 24px;
}

.field-label {
  display: block;
  margin-bottom: 10px;
  font-size: 0.88rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  opacity: 0.72;
}

.choice-row {
  display: flex;
  gap: 12px;
}

.choice-button,
.primary-button,
.secondary-button {
  border: 1px solid currentColor;
  background: transparent;
  color: inherit;
  padding: 12px 16px;
  cursor: pointer;
  font-family: inherit;
}

.choice-button.active {
  background: currentColor;
  color: var(--creator-bg, #fff);
}

.story-input {
  width: 100%;
  min-height: 240px;
  padding: 16px;
  border: 1px solid rgba(127, 127, 127, 0.35);
  background: transparent;
  color: inherit;
  resize: vertical;
  font: inherit;
  line-height: 1.7;
}

.notice {
  margin-top: 18px;
  padding: 14px 16px;
  border: 1px solid rgba(127, 127, 127, 0.35);
}

.notice.error {
  color: #b42318;
}

.action-row {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  margin-top: 24px;
}

.primary-button {
  background: currentColor;
  color: var(--creator-bg, #fff);
}

.primary-button:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

:global(.theme-light) {
  --creator-bg: #f5f0e7;
}

:global(.theme-dark) {
  --creator-bg: #111111;
}

@media (max-width: 720px) {
  .story-creator {
    padding-top: 92px;
  }

  .choice-row,
  .action-row {
    flex-direction: column;
  }

  .choice-button,
  .primary-button,
  .secondary-button {
    width: 100%;
  }
}
</style>
