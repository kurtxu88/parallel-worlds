<template>
  <section class="story-creator">
    <div class="creator-shell">
      <div class="intro-block">
        <p class="eyebrow">{{ t('eyebrow') }}</p>
        <h1>{{ t('title') }}</h1>
        <p class="subtitle">{{ t('subtitle') }}</p>
      </div>

      <div class="seed-gallery">
        <div class="seed-gallery-header">
          <p class="field-label">{{ t('starterSeedsLabel') }}</p>
          <p class="seed-gallery-copy">{{ t('starterSeedsBody') }}</p>
        </div>

        <div class="seed-grid">
          <button
            v-for="seed in seedExamples"
            :key="seed.id"
            class="seed-card"
            :class="{ active: route.query.seed === seed.id }"
            @click="applySeedExample(seed)"
          >
            <span class="seed-title">{{ seed.title }}</span>
            <span class="seed-body">{{ seed.payload.user_input }}</span>
            <span class="seed-action">{{ t('useSeed') }}</span>
          </button>
        </div>
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

        <div class="field-group visibility-block">
          <p class="field-label">{{ t('visibilityLabel') }}</p>
          <label class="visibility-toggle">
            <input v-model="isPublic" type="checkbox" />
            <span>{{ t('publicToggle') }}</span>
          </label>
          <p class="visibility-copy">{{ t('visibilityHelp') }}</p>
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { type AppLanguage, createStory, getStories, type StoryRecord } from '../lib/api'
import { ensureGuestUser } from '../lib/guestSession'
import { getStorySeedExamples, type StorySeedExample } from '../lib/storySeeds'
import { usePageSeo } from '../lib/usePageSeo'

const props = defineProps<{
  currentLang: AppLanguage
}>()

const route = useRoute()
const router = useRouter()

const emit = defineEmits<{
  (e: 'story-created', story: StoryRecord): void
  (e: 'navigate', view: string): void
}>()

const storyInput = ref('')
const genderPreference = ref<'male' | 'female'>('male')
const isPublic = ref(false)
const isSubmitting = ref(false)
const errorMessage = ref('')
const existingStories = ref<StoryRecord[]>([])

const translations = {
  'en-US': {
    eyebrow: 'Create',
    title: 'Seed a new world',
    subtitle: 'Describe the kind of life, conflict, and atmosphere you want the generator to build around you.',
    starterSeedsLabel: 'Starter seeds',
    starterSeedsBody: 'Use one of these to explore the system quickly, then rewrite it into your own world premise.',
    useSeed: 'Use this seed',
    identityLabel: 'Who are you in this world?',
    promptLabel: 'World seed',
    visibilityLabel: 'Sharing',
    visibilityHelp: 'Create a public share page for this world so you can link it in posts, demos, and showcases.',
    publicToggle: 'Make this world publicly shareable',
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
    starterSeedsLabel: '示例种子',
    starterSeedsBody: '可以先用这些例子快速体验系统，再改写成你自己的世界设定。',
    useSeed: '使用这个种子',
    identityLabel: '你在这个世界中是谁？',
    promptLabel: '世界种子',
    visibilityLabel: '分享设置',
    visibilityHelp: '为这个世界创建一个公开分享页，方便你在帖子、demo 和 showcase 中直接传播。',
    publicToggle: '让这个世界可公开分享',
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
const seedExamples = computed(() => getStorySeedExamples(props.currentLang))

usePageSeo({
  title:
    props.currentLang === 'en-US'
      ? 'Create a World | Parallel Worlds'
      : '创建世界 | Parallel Worlds',
  description:
    props.currentLang === 'en-US'
      ? 'Start with a narrative seed, generate a world asynchronously, and step into an open-source interactive story flow.'
      : '从一个叙事种子开始，异步生成世界，并进入一个开源的互动故事流程。',
  path: '/create'
})

const hasPendingStory = computed(() =>
  existingStories.value.some(story => ['pending', 'generating'].includes(story.status))
)

function applySeedExample(seed: StorySeedExample) {
  storyInput.value = seed.payload.user_input
  genderPreference.value = seed.payload.gender_preference
  errorMessage.value = ''
  void router.replace({
    query: {
      ...route.query,
      seed: seed.id,
      prompt: undefined,
      gender: undefined
    }
  })
}

function applySeedFromRoute() {
  const seedId = typeof route.query.seed === 'string' ? route.query.seed : null
  if (seedId) {
    const seed = seedExamples.value.find(item => item.id === seedId)
    if (seed) {
      storyInput.value = seed.payload.user_input
      genderPreference.value = seed.payload.gender_preference
      return
    }
  }

  const prompt = typeof route.query.prompt === 'string' ? route.query.prompt : null
  const gender = route.query.gender === 'female' ? 'female' : 'male'

  if (prompt) {
    storyInput.value = prompt
    genderPreference.value = gender
  }
}

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
      culture_language: props.currentLang,
      is_public: isPublic.value
    })
    emit('story-created', story)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('createFailed')
  } finally {
    isSubmitting.value = false
  }
}

onMounted(async () => {
  applySeedFromRoute()

  try {
    await refreshStories()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : t('createFailed')
  }
})

watch(
  () => [route.query.seed, route.query.prompt, route.query.gender, props.currentLang],
  () => {
    applySeedFromRoute()
  }
)
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

.seed-gallery {
  display: grid;
  gap: 18px;
}

.seed-gallery-header {
  max-width: 64ch;
}

.seed-gallery-copy {
  margin: 0;
  line-height: 1.7;
  opacity: 0.78;
}

.seed-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
}

.seed-card {
  display: grid;
  gap: 12px;
  text-align: left;
  border: 1px solid rgba(127, 127, 127, 0.28);
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.05), transparent),
    radial-gradient(circle at top right, rgba(217, 119, 6, 0.1), transparent 35%);
  color: inherit;
  padding: 18px;
  cursor: pointer;
  font: inherit;
}

.seed-card.active {
  border-color: rgba(244, 178, 110, 0.75);
  box-shadow: 0 0 0 1px rgba(244, 178, 110, 0.25);
}

.seed-title {
  font-size: 1rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.seed-body {
  line-height: 1.75;
  opacity: 0.82;
}

.seed-action {
  font-size: 0.8rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.7;
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

.visibility-block {
  display: grid;
  gap: 10px;
}

.visibility-toggle {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  cursor: pointer;
}

.visibility-toggle input {
  width: 18px;
  height: 18px;
}

.visibility-copy {
  margin: 0;
  line-height: 1.7;
  opacity: 0.76;
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

  .seed-grid {
    grid-template-columns: 1fr;
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
