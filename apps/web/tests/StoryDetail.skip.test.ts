import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { computed, nextTick } from 'vue'
import StoryDetail from '../src/components/StoryDetail.vue'

vi.mock('../src/lib/guestSession', () => ({
  ensureGuestUser: vi.fn().mockResolvedValue('guest-user-1')
}))

vi.mock('../src/lib/api', () => ({
  getApiBaseUrl: vi.fn().mockReturnValue('http://localhost:8000'),
  getStory: vi.fn().mockResolvedValue({
    id: 'story-record-1',
    story_id: 'story-graph-1',
    status: 'completed'
  }),
  getStoryEvents: vi.fn().mockResolvedValue([])
}))

vi.mock('../src/lib/tabManager', () => ({
  useTabManager: () => ({
    isActiveTab: computed(() => true),
    otherTabActive: computed(() => false),
    forceActivateTab: vi.fn()
  })
}))

const mockGameState = {
  current_episode: 1,
  scene_interaction_count: 11,
  current_scene: {
    id: 'scene_1',
    type: 'normal'
  },
  available_choices: [
    {
      index: 0,
      choice_text: 'Enter the castle gates',
      internal_reasoning: 'The main entrance',
      is_hidden: false
    },
    {
      index: 1,
      choice_text: 'Climb the wall',
      internal_reasoning: 'A risky approach',
      is_hidden: false
    },
    {
      index: 2,
      choice_text: 'Wait for nightfall',
      internal_reasoning: 'Patience might pay off',
      is_hidden: false
    },
    {
      index: 3,
      choice_text: 'Use magic portal',
      internal_reasoning: 'Requires hidden knowledge',
      is_hidden: true
    }
  ]
}

describe('StoryDetail skip scene UI', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
    Element.prototype.scrollIntoView = vi.fn()
  })

  async function mountWithGameState() {
    const wrapper = mount(StoryDetail, {
      props: {
        originalStoryId: 'story-record-1',
        currentLang: 'en-US'
      }
    })

    await nextTick()
    ;(wrapper.vm as any).storySegments = ['Opening line']
    ;(wrapper.vm as any).conversationHistory = [{ role: 'assistant', content: 'Opening line' }]
    ;(wrapper.vm as any).gameState = mockGameState
    await nextTick()

    return wrapper
  }

  it('shows the skip button after enough rounds in a scene', async () => {
    const wrapper = await mountWithGameState()

    expect(wrapper.find('.skip-scene-section').exists()).toBe(true)
    expect(wrapper.find('.skip-scene-button').text()).toBe('Skip to Next Scene')
    expect(wrapper.find('.skip-scene-hint').text()).toContain('11 rounds')
  })

  it('renders only non-hidden skip choices', async () => {
    const wrapper = await mountWithGameState()

    await wrapper.find('.skip-scene-button').trigger('click')
    await nextTick()

    const choices = wrapper.findAll('.skip-choice-item')
    expect(choices).toHaveLength(3)
    expect(wrapper.text()).toContain('Enter the castle gates')
    expect(wrapper.text()).not.toContain('Use magic portal')
  })

  it('hides the skip action for ending scenes', async () => {
    const wrapper = await mountWithGameState()
    ;(wrapper.vm as any).gameState = {
      ...mockGameState,
      current_scene: {
        id: 'scene_ending',
        type: 'ending'
      }
    }
    await nextTick()

    expect(wrapper.find('.skip-scene-section').exists()).toBe(false)
  })

  it('switches skip-scene copy in Chinese', async () => {
    const wrapper = await mountWithGameState()

    await wrapper.setProps({ currentLang: 'zh-CN' })
    await nextTick()

    expect(wrapper.find('.skip-scene-button').text()).toBe('跳到下一个场景')
  })
})
