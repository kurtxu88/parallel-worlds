<template>
  <main class="landing-page">
    <section class="hero">
      <div class="hero-copy">
        <p class="eyebrow">{{ t('eyebrow') }}</p>
        <h1>{{ t('title') }}</h1>
        <p class="subtitle">{{ t('subtitle') }}</p>
        <div class="hero-actions">
          <router-link class="primary-link" :to="{ name: 'create' }">
            {{ t('startCreating') }}
          </router-link>
          <router-link class="secondary-link" :to="{ name: 'worlds' }">
            {{ t('browseWorlds') }}
          </router-link>
        </div>
      </div>

      <aside class="hero-panel">
        <p class="panel-label">{{ t('panelLabel') }}</p>
        <ul class="feature-list">
          <li>{{ t('feature1') }}</li>
          <li>{{ t('feature2') }}</li>
          <li>{{ t('feature3') }}</li>
        </ul>
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
      </aside>
    </section>

    <section class="steps">
      <article class="step-card">
        <p class="step-index">01</p>
        <h2>{{ t('step1Title') }}</h2>
        <p>{{ t('step1Body') }}</p>
      </article>
      <article class="step-card">
        <p class="step-index">02</p>
        <h2>{{ t('step2Title') }}</h2>
        <p>{{ t('step2Body') }}</p>
      </article>
      <article class="step-card">
        <p class="step-index">03</p>
        <h2>{{ t('step3Title') }}</h2>
        <p>{{ t('step3Body') }}</p>
      </article>
    </section>
  </main>
</template>

<script setup lang="ts">
import type { AppLanguage } from '../lib/api'

const props = defineProps<{
  currentLang: AppLanguage
}>()

const emit = defineEmits<{
  (e: 'language-change', language: AppLanguage): void
}>()

const translations = {
  'en-US': {
    eyebrow: 'Open-source AI storytelling',
    title: 'Build worlds. Enter them. Change them from inside.',
    subtitle: 'Parallel Worlds is a Vue + FastAPI app for generating graph-backed interactive story worlds with Neo4j and Postgres.',
    startCreating: 'Create a world',
    browseWorlds: 'Open my worlds',
    panelLabel: 'Open-source release v1',
    feature1: 'Guest mode, no hosted auth',
    feature2: 'Async world generation worker',
    feature3: 'Streaming play sessions with history restore',
    step1Title: 'Seed the premise',
    step1Body: 'Describe your character, tension, and setting in a few lines. The backend turns that seed into a world graph.',
    step2Title: 'Wait for generation',
    step2Body: 'A background worker claims pending jobs, generates the story structure, and writes the finished world back for play.',
    step3Title: 'Play in-stream',
    step3Body: 'Enter the world, send actions to the FastAPI game endpoint, and restore the full conversation later from stored events.'
  },
  'zh-CN': {
    eyebrow: '开源 AI 互动叙事',
    title: '构建世界，进入世界，并从世界内部改变它。',
    subtitle: 'Parallel Worlds 是一个基于 Vue + FastAPI 的开源项目，使用 Neo4j 和 Postgres 生成并游玩图结构互动故事世界。',
    startCreating: '创建世界',
    browseWorlds: '打开我的世界',
    panelLabel: '开源首发版 v1',
    feature1: '访客模式，无托管认证',
    feature2: '异步世界生成 worker',
    feature3: '支持历史恢复的流式游玩会话',
    step1Title: '播下设定种子',
    step1Body: '用几句话描述角色、冲突和场景，后端会把它扩展成一个完整的世界图谱。',
    step2Title: '等待生成完成',
    step2Body: '后台 worker 会领取待处理任务，生成故事结构，并把完成后的世界写回供玩家进入。',
    step3Title: '流式进入世界',
    step3Body: '通过 FastAPI 游戏接口发送行动，并在之后通过事件历史恢复完整对话。'
  }
} as const

const t = (key: keyof typeof translations['en-US']) => translations[props.currentLang][key]
</script>

<style scoped>
.landing-page {
  min-height: 100vh;
  padding: 120px 20px 64px;
  font-family: monospace;
  background:
    radial-gradient(circle at top left, rgba(217, 119, 6, 0.18), transparent 30%),
    radial-gradient(circle at bottom right, rgba(21, 128, 61, 0.16), transparent 30%);
}

.hero {
  width: min(1120px, 100%);
  margin: 0 auto 40px;
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(280px, 0.9fr);
  gap: 22px;
}

.hero-copy,
.hero-panel,
.step-card {
  border: 1px solid rgba(127, 127, 127, 0.28);
  background: rgba(255, 255, 255, 0.42);
  backdrop-filter: blur(8px);
}

.hero-copy {
  padding: 36px;
}

.hero-panel {
  padding: 28px;
  align-self: start;
}

.eyebrow,
.panel-label,
.step-index {
  margin: 0 0 10px;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 0.74rem;
  opacity: 0.7;
}

h1 {
  margin: 0 0 16px;
  font-size: clamp(2.8rem, 7vw, 5.4rem);
  line-height: 0.98;
}

.subtitle,
.step-card p,
.feature-list {
  line-height: 1.7;
}

.hero-actions,
.language-row {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-top: 24px;
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
  color: var(--landing-bg, #fff);
}

.feature-list {
  padding-left: 18px;
  margin: 0;
}

.steps {
  width: min(1120px, 100%);
  margin: 0 auto;
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 18px;
}

.step-card {
  padding: 24px;
}

.step-card h2 {
  margin: 0 0 12px;
  font-size: 1.2rem;
}

:global(.theme-light) {
  --landing-bg: #f5f0e7;
}

:global(.theme-dark) {
  --landing-bg: #111111;
}

@media (max-width: 860px) {
  .landing-page {
    padding-top: 92px;
  }

  .hero,
  .steps {
    grid-template-columns: 1fr;
  }

  .hero-copy,
  .hero-panel,
  .step-card {
    padding: 24px;
  }
}
</style>
