import type { AppLanguage, StoryCreatePayload } from './api'

export interface StorySeedExample {
  id: string
  title: string
  payload: StoryCreatePayload
}

const STORY_SEED_EXAMPLES: Record<AppLanguage, StorySeedExample[]> = {
  'en-US': [
    {
      id: 'drowned-moon',
      title: 'Drowned Moon Archives',
      payload: {
        user_input:
          'An archivist on a drowned moon keeps discovering records of wars that have not happened yet.',
        gender_preference: 'female',
        culture_language: 'en-US',
        is_public: false
      }
    },
    {
      id: 'leviathan-city',
      title: 'City on a Sleeping Leviathan',
      payload: {
        user_input:
          'A cartographer in a cliffside city realizes the streets shift because the entire metropolis is built on a sleeping leviathan.',
        gender_preference: 'male',
        culture_language: 'en-US',
        is_public: false
      }
    },
    {
      id: 'winter-orchard',
      title: 'The Orchard That Forgets',
      payload: {
        user_input:
          'Each winter, a village orchard erases one memory from everyone who walks beneath it, and this year your missing memory was a person.',
        gender_preference: 'female',
        culture_language: 'en-US',
        is_public: false
      }
    }
  ],
  'zh-CN': [
    {
      id: 'drowned-moon',
      title: '溺月档案馆',
      payload: {
        user_input: '一位住在被海水吞没之月上的档案管理员，不断发现记录着“尚未发生的战争”的卷宗。',
        gender_preference: 'female',
        culture_language: 'zh-CN',
        is_public: false
      }
    },
    {
      id: 'leviathan-city',
      title: '沉睡巨兽之城',
      payload: {
        user_input: '一名地图绘制师发现悬崖之城的街道之所以不断改变，是因为整座城市建在一头沉睡巨兽的背上。',
        gender_preference: 'male',
        culture_language: 'zh-CN',
        is_public: false
      }
    },
    {
      id: 'winter-orchard',
      title: '遗忘果园',
      payload: {
        user_input: '每到冬天，村中的果园都会夺走每个路过之人的一段记忆，而你今年失去的记忆竟然是“某个人”。',
        gender_preference: 'female',
        culture_language: 'zh-CN',
        is_public: false
      }
    }
  ]
}

export function getStorySeedExamples(language: AppLanguage) {
  return STORY_SEED_EXAMPLES[language]
}
