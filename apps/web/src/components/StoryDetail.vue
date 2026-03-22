<template>
  <div class="story-detail">
    <!-- Show start button if no story segments -->
    <div v-if="storySegments.length === 0" class="start-section">
      <div class="start-message">
        {{ props.currentLang === 'en-US' ? 'Ready to enter this world?' : '准备进入这个世界吗？' }}
      </div>
      <button @click="handleGameStart" class="start-button" :disabled="isStarting">
        {{ isStarting ? (props.currentLang === 'en-US' ? 'Entering...' : '正在进入...') : (props.currentLang === 'en-US' ? 'Enter World' : '开始进入') }}
      </button>
    </div>
    
    <!-- Story segments -->
    <div v-else class="story-segments">
      <div 
        v-for="(segment, index) in displaySegments" 
        :key="index" 
        class="segment"
        :class="{ 'user-input': conversationHistory[index]?.role === 'user' }"
      >
        {{ segment }}
      </div>
    </div>
    
    <!-- Simple input section -->
    <div v-if="storySegments.length > 0" class="input-section">
      <div class="input-group">
        <div class="input-label">{{ inputLabel }}</div>
        <div class="message user">
          <pre
            contenteditable="true"
            @keydown="handleKeyDown"
            @input="handleInput"
            ref="inputRef"
            class="editable-message"
            :class="{ 'empty': !userInput }"
            :disabled="isStreaming || !isActiveTab"
            :data-placeholder="inputPlaceholder"
          ></pre>
        </div>
      </div>
      
      <!-- Skip to next scene button -->
      <div v-if="canSkipScene && !isStreaming" class="skip-scene-section">
        <div class="skip-scene-hint">
          {{ props.currentLang === 'en-US' 
            ? `You've been in this scene for ${gameState.scene_interaction_count} rounds.` 
            : `你已经在这个场景中进行了 ${gameState.scene_interaction_count} 回合。` }}
        </div>
        <button @click="showSkipChoices = true" class="skip-scene-button">
          {{ props.currentLang === 'en-US' ? 'Skip to Next Scene' : '跳到下一个场景' }}
        </button>
      </div>
      
      <!-- Bottom padding to ensure skip button is visible -->
      <div class="bottom-spacer"></div>
      
      <!-- Skip Scene Choice Modal -->
      <div v-if="showSkipChoices" class="skip-choice-modal">
        <div class="skip-choice-overlay" @click="showSkipChoices = false"></div>
        <div class="skip-choice-content">
          <h3>{{ props.currentLang === 'en-US' ? 'Choose your path to the next scene:' : '选择通往下一个场景的路径：' }}</h3>
          <p class="skip-choice-note">
            {{ props.currentLang === 'en-US' 
              ? 'Choose one of the generated transitions to move the story forward.'
              : '选择一个已生成的过渡行动，让故事继续向前推进。' }}
          </p>
          <div class="skip-choices">
            <template v-for="(choice, index) in gameState?.available_choices" :key="index">
              <div v-if="!choice.is_hidden"
                   class="skip-choice-item"
                   @click="handleSkipWithChoice(choice)">
                <div class="choice-text">{{ choice.choice_text }}</div>
                <div v-if="choice.internal_reasoning" class="choice-hint">
                  {{ choice.internal_reasoning }}
                </div>
              </div>
            </template>
          </div>
          <button @click="showSkipChoices = false" class="cancel-button">
            {{ props.currentLang === 'en-US' ? 'Cancel' : '取消' }}
          </button>
        </div>
      </div>
    </div>
    
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, computed, watch } from 'vue'
import { useTabManager } from '../lib/tabManager'
import {
  getApiBaseUrl,
  getStory,
  getStoryEvents,
  type AppLanguage
} from '../lib/api'
import { ensureGuestUser } from '../lib/guestSession'
import { usePageSeo } from '../lib/usePageSeo'

// Props to receive the selected story
const props = defineProps<{
  originalStoryId: string
  currentLang: AppLanguage
}>()

usePageSeo({
  title:
    props.currentLang === 'en-US'
      ? 'World Session | Parallel Worlds'
      : '世界会话 | Parallel Worlds',
  description:
    props.currentLang === 'en-US'
      ? 'Play inside a generated world and restore the session from stored interaction history.'
      : '进入一个已生成的世界，并从已保存的互动历史中恢复会话。',
  path: `/world/${props.originalStoryId}`,
  noindex: true
})

// Reactive state for user input
const userInput = ref('')

// Story segments 
const storySegments = ref<string[]>([])

// Current session data
const currentSessionId = ref<string>('')

// Graph story ID used by the backend game engine
const graphStoryId = ref<string>('')

const inputRef = ref<HTMLPreElement>()

// Content filter function
function filterTechnicalMarkers(text: string): string {
  if (!text) return ''
  
  // Filter out technical markers
  let filtered = text
    .replace(/\[EVENT_COMPLETED:[^\]]*\]/g, '')  // EVENT_COMPLETED markers
    .replace(/\[SCENE_TRANSITION:[^\]]*\]/g, '')  // Scene transition markers
    .replace(/CHOICE_SELECTED:\s*\d+/g, '')  // Choice selection markers
  
  // Clean up excessive whitespace
  filtered = filtered
    .replace(/\n\s*\n\s*\n/g, '\n\n')  // Multiple blank lines to double
    .trim()
  
  return filtered
}

// Buffer for handling split technical markers in streaming
let streamingBuffer = ''

// Process streaming content with buffer to handle split markers
function processStreamingContent(content: string): string {
  // Add to buffer
  streamingBuffer += content
  
  // Check for incomplete EVENT_COMPLETED marker
  const lastOpenBracket = streamingBuffer.lastIndexOf('[EVENT_COMPLETED:')
  
  if (lastOpenBracket !== -1) {
    const closeBracket = streamingBuffer.indexOf(']', lastOpenBracket)
    
    if (closeBracket === -1) {
      // Marker is incomplete, only process content before it
      const safeContent = streamingBuffer.substring(0, lastOpenBracket)
      streamingBuffer = streamingBuffer.substring(lastOpenBracket)
      return safeContent
    }
  }
  
  // No incomplete markers, process entire buffer
  const content_to_process = streamingBuffer
  streamingBuffer = ''
  return content_to_process
}

// State management variables
const guestUserId = ref<string>('')

const isStarting = ref(false) // Track game start state
const isStreaming = ref(false) // Track streaming state
const showSkipChoices = ref(false) // Track skip choice modal

// Game state management
const conversationHistory = ref<{
  role: string, 
  content: string, 
  timestamp?: string,
  episode_number?: number,
  scene_id?: string,
  round_number?: number
}[]>([])
const gameState = ref<any>(null)

// Tab manager
const { isActiveTab } = useTabManager()

// Filtered story segments for display
const displaySegments = computed(() => {
  return storySegments.value.map(segment => filterTechnicalMarkers(segment))
})

const API_BASE_URL = getApiBaseUrl()

// Computed properties for labels based on script language
const inputLabel = computed(() => {
  // Check if there are available choices in the game state
  const hasChoices = gameState.value?.available_choices?.length > 0
  
  if (props.currentLang === 'en-US') {
    if (hasChoices) {
      return 'Your action (choose an option or create your own):'
    }
    return 'What do you do? (Type your action):'
  } else {
    if (hasChoices) {
      return '你的选择（选择选项或自由发挥）：'
    }
    return '你想做什么？（输入你的行动）：'
  }
})

const inputPlaceholder = computed(() => {
  return props.currentLang === 'en-US' 
    ? 'Type a number or describe your action...' 
    : '输入数字或描述你的行动...'
})

// Check if current scene has exceeded 10 rounds
const canSkipScene = computed(() => {
  return (
    gameState.value?.scene_interaction_count >= 10 &&
    gameState.value?.current_scene?.type !== 'ending'
  )
})

// Watch for skip button appearance and scroll into view
watch(canSkipScene, async (newValue) => {
  if (newValue) {
    // Wait for DOM update
    await nextTick()
    // Find the skip button and scroll it into view
    const skipSection = document.querySelector('.skip-scene-section')
    if (skipSection) {
      skipSection.scrollIntoView({ behavior: 'smooth', block: 'center' })
    }
  }
})

onMounted(async () => {
  guestUserId.value = await ensureGuestUser()
  await loadStoryHistory()
  
  // Focus on input if it exists
  await nextTick()
  if (inputRef.value) {
    inputRef.value.focus()
  }
})

watch(
  () => props.originalStoryId,
  async (newId, oldId) => {
    if (!guestUserId.value || !newId || newId === oldId) {
      return
    }
    await loadStoryHistory()
  }
)

// Handle input
function handleInput(event: Event) {
  if (isStreaming.value) return // Disable input during streaming
  
  const target = event.target as HTMLElement
  let text = target.innerText || target.textContent || ''
  
  if (text !== userInput.value) {
    userInput.value = text
  }
}

// Handle key down events for the input
function handleKeyDown(event: KeyboardEvent) {
  if (isStreaming.value) {
    event.preventDefault()
    return
  }
  
  if (event.key === 'Enter') {
    event.preventDefault()
    const inputText = userInput.value.trim()
    if (inputText) {
      handleSubmit()
    }
  }
}

// Handle submission via FastAPI
async function handleSubmit() {
  const inputText = userInput.value.trim()
  
  if (!inputText || isStreaming.value) return
  
  // Check if tab is active
  if (!isActiveTab.value) {
    console.warn('Cannot submit - tab is not active')
    return
  }
  
  console.log('Submitting user input to FastAPI...')
  
  try {
    isStreaming.value = true
    
    // Add user input to story segments immediately for better UX
    storySegments.value.push(inputText)
    
    // Add to conversation history
    conversationHistory.value.push({
      role: 'user',
      content: inputText,
      timestamp: new Date().toISOString(),
      episode_number: gameState.value?.current_episode,
      scene_id: gameState.value?.current_scene?.id,
      round_number: gameState.value?.scene_interaction_count
    })
    
    // Clear input
    userInput.value = ''
    if (inputRef.value) {
      inputRef.value.innerText = ''
    }
    
    // Call FastAPI streaming endpoint
    await callFastAPIStream('user_input', inputText)
    
  } catch (error) {
    console.error('Error submitting input:', error)
    // Remove the user input from segments if there was an error
    storySegments.value.pop()
    conversationHistory.value.pop()
  } finally {
    isStreaming.value = false
  }
}

// Handle game start via FastAPI
async function handleGameStart() {
  if (isStarting.value) return
  
  isStarting.value = true
  console.log('Starting game via FastAPI...')
  
  try {
    // Call FastAPI streaming endpoint to start the game
    await callFastAPIStream('game_start', '')
    
  } catch (error) {
    console.error('Error starting game:', error)
  } finally {
    isStarting.value = false
  }
}

// Handle skip to next scene with choice
async function handleSkipWithChoice(choice: any) {
  if (isStreaming.value) return
  
  // Check if tab is active
  if (!isActiveTab.value) {
    console.warn('Cannot skip scene - tab is not active')
    return
  }
  
  showSkipChoices.value = false
  
  console.log('Requesting to skip to next scene with choice:', choice.choice_text)
  
  try {
    isStreaming.value = true
    
    // Add a system message indicating scene skip with choice
    const skipMessage = props.currentLang === 'en-US' 
      ? `[Choosing: ${choice.choice_text}]` 
      : `[选择：${choice.choice_text}]`
    
    storySegments.value.push(skipMessage)
    
    // Add to conversation history
    conversationHistory.value.push({
      role: 'user',
      content: choice.choice_text,
      timestamp: new Date().toISOString(),
      episode_number: gameState.value?.current_episode,
      scene_id: gameState.value?.current_scene?.id,
      round_number: gameState.value?.scene_interaction_count
    })
    
    // Call FastAPI with the selected choice text
    // The backend will match this against available choices
    await callFastAPIStream('skip_scene', choice.choice_text)
    
  } catch (error) {
    console.error('Error skipping scene:', error)
    // Remove the skip message if there was an error
    storySegments.value.pop()
    conversationHistory.value.pop()
  } finally {
    isStreaming.value = false
  }
}

// Call FastAPI streaming endpoint
async function callFastAPIStream(requestType: string, userInputText: string) {
  try {
    if (!graphStoryId.value || !guestUserId.value) {
      throw new Error('Story context not loaded')
    }
    
    const requestData = {
      user_id: guestUserId.value,
      story_id: graphStoryId.value,
      request_type: requestType,
      user_input: userInputText,
      session_id: currentSessionId.value,
      conversation_history: conversationHistory.value,
      game_state: gameState.value
    }
    
    console.log('Sending request to FastAPI:', requestData)
    
    const response = await fetch(`${API_BASE_URL}/api/game/interact`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'X-User-Id': guestUserId.value
      },
      body: JSON.stringify(requestData)
    })
    
    if (!response.ok) {
      throw new Error(`FastAPI request failed: ${response.status}`)
    }
    
    // Handle streaming response
    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('No response body reader available')
    }
    
    const decoder = new TextDecoder()
    let currentResponse = ''
    let responseStarted = false
    let buffer = ''
    
    while (true) {
      const { done, value } = await reader.read()
      
      if (done) {
        // Process any remaining buffered content when stream ends
        if (streamingBuffer) {
          currentResponse += streamingBuffer
          streamingBuffer = ''
          
          // Update the last segment
          if (storySegments.value.length > 0) {
            const lastIndex = storySegments.value.length - 1
            storySegments.value.splice(lastIndex, 1, currentResponse)
          }
        }
        break
      }
      
      const chunk = decoder.decode(value, { stream: true })
      buffer += chunk
      
      
      // Process complete lines ending with \n\n (SSE format)
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || '' // Keep incomplete line in buffer
      
      for (const line of lines) {
        // Skip empty lines
        if (!line) continue
        
        // Handle lines that might have leading newlines due to SSE format
        if (line.startsWith('data: ')) {
          const content = line.substring(6) // Remove 'data: ' prefix
          
          if (content === '[END]') {
            // End of stream
            console.log('Stream ended')
            if (currentResponse.trim()) {
              // Add final response to conversation history
              conversationHistory.value.push({
                role: 'assistant',
                content: currentResponse.trim(),
                timestamp: new Date().toISOString(),
                episode_number: gameState.value?.current_episode,
                scene_id: gameState.value?.current_scene?.id,
                round_number: gameState.value?.scene_interaction_count
              })
            }
            return
          } else if (content.startsWith('[ERROR]')) {
            console.error('FastAPI error:', content)
            throw new Error(content)
          } else if (content.startsWith('[SCENE_TRANSITION]')) {
            const sceneId = content.substring(18).trim()
            console.log('Scene transition:', sceneId)
            
            // Save current response if any
            if (currentResponse.trim()) {
              conversationHistory.value.push({
                role: 'assistant',
                content: currentResponse.trim(),
                timestamp: new Date().toISOString(),
                episode_number: gameState.value?.current_episode,
                scene_id: gameState.value?.current_scene?.id,
                round_number: gameState.value?.scene_interaction_count
              })
            }
            
            // Reset for new scene
            currentResponse = ''
            responseStarted = false
          } else if (content.startsWith('[GAME_STATE]')) {
            const stateJson = content.substring(12).trim()
            try {
              gameState.value = JSON.parse(stateJson)
              console.log('Updated game state:', gameState.value)
            } catch (e) {
              console.warn('Failed to parse game state:', e)
            }
            // Important: Don't add GAME_STATE to the displayed content
            continue
          } else if (content.startsWith('[CONNECTION_LOST]')) {
            console.warn('Connection lost')
            throw new Error('Connection lost')
          } else if (content.startsWith('[GAME_START]')) {
            console.log('Game started')
            // Don't add to displayed content
            continue
          } else if (content.startsWith('[STORY_ENDED]')) {
            console.log('Story ended')
            // Don't add to displayed content
            continue
          } else {
            // Regular content chunk
            if (!responseStarted) {
              responseStarted = true
              // Add empty placeholder for streaming response
              storySegments.value.push('')
              // Reset buffer for new response
              streamingBuffer = ''
            }
            
            // Process content through buffer to handle split markers
            const processedContent = processStreamingContent(content)
            
            // Add processed content to response
            if (processedContent === '') {
              // Empty content might mean we're buffering an incomplete marker
              // Don't add newline in this case
            } else {
              currentResponse += processedContent
            }
            
            // Update the last segment with accumulated response
            if (storySegments.value.length > 0) {
              // Force Vue to detect the change by using array splice
              const lastIndex = storySegments.value.length - 1
              storySegments.value.splice(lastIndex, 1, currentResponse)
            }
          }
        } else if (line.trim() && line.includes('data: ')) {
          // Handle case where there might be leading newlines
          const dataIndex = line.indexOf('data: ')
          if (dataIndex !== -1) {
            const content = line.substring(dataIndex + 6)
            // Add any leading characters (likely newlines) before 'data:'
            const leadingChars = line.substring(0, dataIndex)
            
            // Process content through buffer
            const processedContent = processStreamingContent(content)
            if (processedContent) {
              currentResponse += leadingChars + processedContent
            }
            
            // Update the last segment
            if (storySegments.value.length > 0) {
              const lastIndex = storySegments.value.length - 1
              storySegments.value.splice(lastIndex, 1, currentResponse)
            }
          }
        }
      }
    }
    
  } catch (error) {
    console.error('FastAPI streaming error:', error)
    throw error
  }
}

const loadStoryHistory = async () => {
  try {
    if (!guestUserId.value) {
      return
    }

    const storyRecord = await getStory(guestUserId.value, props.originalStoryId)
    graphStoryId.value = storyRecord.story_id

    if (storyRecord.status !== 'completed' || !graphStoryId.value) {
      currentSessionId.value = crypto.randomUUID()
      storySegments.value = []
      conversationHistory.value = []
      gameState.value = null
      return
    }

    const storyEvents = await getStoryEvents(guestUserId.value, props.originalStoryId)

    if (storyEvents.length > 0) {
      const segments: string[] = []
      const history: {
        role: string, 
        content: string, 
        timestamp?: string,
        episode_number?: number,
        scene_id?: string,
        round_number?: number
      }[] = []
      let latestSessionId = ''
      
      storyEvents.forEach(event => {
        if (event.content) {
          segments.push(event.content)
          
          // Convert to conversation history format
          const role = event.event_type === 'user_input' ? 'user' : 'assistant'
          history.push({
            role: role,
            content: event.content,
            timestamp: event.created_at,
            episode_number: event.episode_number ?? undefined,
            scene_id: event.scene_id ?? undefined,
            round_number: event.round_number ?? undefined
          })
        }
        if (event.session_id) {
          latestSessionId = event.session_id
        }
      })
      
      storySegments.value = segments
      conversationHistory.value = history
      currentSessionId.value = latestSessionId || crypto.randomUUID()
      
      if (history.length > 0) {
        const lastEntry = history[history.length - 1]
        const latestSceneId = lastEntry.scene_id || 'S1'
        const latestEpisode = lastEntry.episode_number || 1
        
        let currentSceneCount = 0
        for (let i = history.length - 1; i >= 0; i--) {
          if (history[i].scene_id === latestSceneId && history[i].episode_number === latestEpisode) {
            if (history[i].role === 'user' && history[i].round_number) {
              currentSceneCount = Math.max(currentSceneCount, history[i].round_number || 0)
            }
          } else {
            break
          }
        }
        
        gameState.value = {
          current_scene: {
            id: latestSceneId,
            episode: latestEpisode
          },
          current_episode: latestEpisode,
          scene_interaction_count: currentSceneCount + 1,
          story_flags: {},
          scene_history: [],
          available_choices: []
        }
      }
    } else {
      currentSessionId.value = crypto.randomUUID()
      storySegments.value = []
      conversationHistory.value = []
      gameState.value = null
    }
  } catch (error) {
    console.error('Error loading story history:', error)
    currentSessionId.value = crypto.randomUUID()
    storySegments.value = []
    conversationHistory.value = []
    gameState.value = null
  }
}

</script>

<style scoped>
/* CSS Variables for theming */
:global(.theme-light) {
  --start-message-color: #666;
  --start-button-border-color: #333;
  --start-button-text-color: #333;
  --start-button-hover-bg: #333;
  --start-button-hover-text: white;
  --segment-color: #333;
  --segment-border-color: #eee;
  --segment-user-opacity: 0.7;
  --input-section-border-color: #eee;
  --input-label-color: #666;
  --message-user-color: #333;
  --message-user-bg: rgba(0, 0, 0, 0.02);
  --message-user-hover-bg: rgba(0, 0, 0, 0.04);
  --editable-message-color: #333;
  --editable-placeholder-color: #999;
  --keyboard-nav-footer-color: #666;
  --skip-button-bg-hover: white;
}

:global(.theme-dark) {
  --start-message-color: #999;
  --start-button-border-color: #e0e0e0;
  --start-button-text-color: #e0e0e0;
  --start-button-hover-bg: #e0e0e0;
  --start-button-hover-text: #000;
  --segment-color: #e0e0e0;
  --segment-border-color: #333;
  --segment-user-opacity: 0.6;
  --input-section-border-color: #333;
  --input-label-color: #999;
  --message-user-color: #e0e0e0;
  --message-user-bg: rgba(255, 255, 255, 0.04);
  --message-user-hover-bg: rgba(255, 255, 255, 0.06);
  --editable-message-color: #e0e0e0;
  --editable-placeholder-color: #666;
  --keyboard-nav-footer-color: #999;
  --skip-button-bg-hover: #1a1a1a;
}

/* Default fallback for system theme */
@media (prefers-color-scheme: light) {
  :root {
    --start-message-color: #666;
    --start-button-border-color: #333;
    --start-button-text-color: #333;
    --start-button-hover-bg: #333;
    --start-button-hover-text: white;
    --segment-color: #333;
    --segment-border-color: #eee;
    --segment-user-opacity: 0.7;
    --input-section-border-color: #eee;
    --input-label-color: #666;
    --message-user-color: #333;
    --message-user-bg: rgba(0, 0, 0, 0.02);
    --message-user-hover-bg: rgba(0, 0, 0, 0.04);
    --editable-message-color: #333;
    --editable-placeholder-color: #999;
    --keyboard-nav-footer-color: #666;
    --skip-button-bg-hover: white;
  }
}

@media (prefers-color-scheme: dark) {
  :root {
    --start-message-color: #999;
    --start-button-border-color: #e0e0e0;
    --start-button-text-color: #e0e0e0;
    --start-button-hover-bg: #e0e0e0;
    --start-button-hover-text: #000;
    --segment-color: #e0e0e0;
    --segment-border-color: #333;
    --segment-user-opacity: 0.6;
    --input-section-border-color: #333;
    --input-label-color: #999;
    --message-user-color: #e0e0e0;
    --message-user-bg: rgba(255, 255, 255, 0.04);
    --message-user-hover-bg: rgba(255, 255, 255, 0.06);
    --editable-message-color: #e0e0e0;
    --editable-placeholder-color: #666;
    --keyboard-nav-footer-color: #999;
    --skip-button-bg-hover: #1a1a1a;
  }
}

.story-detail {
  max-width: 800px;
  width: 100%;
  margin: 0 auto;
  padding: 20px;
  font-family: monospace;
  text-align: left;
  box-sizing: border-box;
  overflow-x: hidden;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
}

/* Mobile responsive styles */
@media (max-width: 768px) {
  .story-detail {
    padding: 15px;
  }
}

@media (max-width: 480px) {
  .story-detail {
    padding: 10px;
  }
}

.start-section {
  text-align: center;
  padding: 60px 20px;
  font-family: monospace;
}

.start-message {
  color: var(--start-message-color);
  margin-bottom: 30px;
  font-size: 1.1em;
  line-height: 1.4;
}

.start-button {
  background: none;
  border: 2px solid var(--start-button-border-color);
  color: var(--start-button-text-color);
  padding: 12px 24px;
  cursor: pointer;
  font-family: monospace;
  font-size: 1em;
  transition: all 0.2s ease;
  outline: none;
  -webkit-tap-highlight-color: transparent;
  user-select: none;
}

.start-button:hover:not(:disabled) {
  background: var(--start-button-hover-bg);
  color: var(--start-button-hover-text);
}

.start-button:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.story-segments {
  margin-bottom: 30px;
  width: 100%;
  overflow-x: auto;
  overflow-y: visible;
}

.segment {
  padding: 15px 10px;
  border-bottom: 1px solid var(--segment-border-color);
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  line-height: 1.4;
  color: var(--segment-color);
  max-width: 100%;
}

.segment.user-input {
  opacity: var(--segment-user-opacity);
}

.segment:last-child {
  border-bottom: none;
}

.input-section {
  border-top: 1px solid var(--input-section-border-color);
  padding-top: 20px;
}

/* Mobile responsive adjustments for input section */
@media (max-width: 768px) {
  .input-section {
    padding-top: 15px;
  }
}

@media (max-width: 480px) {
  .input-section {
    padding-top: 10px;
  }
}

.dual-input-container {
  display: flex;
  flex-direction: column;
  gap: 0px;
}

.input-group {
  display: flex;
  flex-direction: column;
}

.input-label {
  font-size: 0.9em;
  color: var(--input-label-color);
  margin-bottom: 5px;
  padding-left: 10px;
}

.message {
  padding: 10px;
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  line-height: 1.4;
  border: none !important;
  outline: none !important;
  box-shadow: none !important;
  position: relative;
  max-width: 100%;
  overflow-x: auto;
}

.message.user {
  color: var(--message-user-color);
  background-color: var(--message-user-bg);
  border-radius: 4px;
  transition: background-color 0.2s ease;
}

.message.user:hover {
  background-color: var(--message-user-hover-bg);
}

.editable-message {
  width: 100%;
  max-width: 100%;
  border: none !important;
  background: transparent;
  resize: none;
  outline: none !important;
  overflow: hidden;
  -webkit-appearance: none;
  -moz-appearance: none;
  appearance: none;
  box-shadow: none !important;
  font-family: inherit !important;
  margin: 0;
  padding: 0;
  white-space: pre-wrap;
  word-wrap: break-word;
  word-break: break-word;
  overflow-wrap: break-word;
  color: var(--editable-message-color);
  min-height: 1.4em;
}

.editable-message:focus {
  outline: none;
}

.editable-message.empty::before {
  content: attr(data-placeholder);
  color: var(--editable-placeholder-color);
  opacity: 0.6;
  position: absolute;
  pointer-events: none;
}

.editable-message.empty {
  opacity: 0.6;
}

.keyboard-nav-footer {
  margin-top: 30px;
  text-align: center;
  color: var(--keyboard-nav-footer-color);
  font-size: 0.8em;
}

.bottom-spacer {
  height: 50px;
}

.editable-message:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Skip scene section styles */
.skip-scene-section {
  margin-top: 20px;
  padding-top: 20px;
  border-top: 1px solid var(--input-section-border-color);
  text-align: center;
}

.skip-scene-hint {
  font-size: 0.9em;
  color: var(--input-label-color);
  margin-bottom: 10px;
  opacity: 0.8;
}

.skip-scene-button {
  background: none;
  border: 1px solid var(--submit-button-color);
  color: var(--submit-button-color);
  padding: 8px 16px;
  font-family: monospace;
  font-size: 0.9em;
  cursor: pointer;
  transition: all 0.2s ease;
  opacity: 0.7;
}

.skip-scene-button:hover {
  opacity: 1;
  background: var(--submit-button-color);
  color: var(--skip-button-bg-hover);
}

.skip-scene-button:focus {
  outline: none;
  box-shadow: 0 0 0 2px var(--submit-button-color);
}

/* Skip Choice Modal */
.skip-choice-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  z-index: 1000;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
}

.skip-choice-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
}

.skip-choice-content {
  position: relative;
  background: var(--bg-color);
  border: 1px solid var(--border-color);
  padding: 24px;
  max-width: 600px;
  width: 100%;
  max-height: 80vh;
  overflow-y: auto;
  font-family: monospace;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.3);
}

/* Ensure modal has solid background in all themes */
.theme-light .skip-choice-content {
  background: white;
}

.theme-dark .skip-choice-content {
  background: #1a1a1a;
}

/* System theme fallbacks */
@media (prefers-color-scheme: light) {
  :root:not(.theme-dark) .skip-choice-content {
    background: white;
  }
}

@media (prefers-color-scheme: dark) {
  :root:not(.theme-light) .skip-choice-content {
    background: #1a1a1a;
  }
}

.skip-choice-content h3 {
  margin-bottom: 12px;
  font-size: 1.1em;
  font-weight: normal;
  color: var(--text-color);
}

.skip-choice-note {
  margin-bottom: 20px;
  font-size: 0.85em;
  opacity: 0.5;
  color: var(--text-secondary);
  line-height: 1.4;
  text-align: center;
  font-style: italic;
  letter-spacing: 0.5px;
}

.skip-choices {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
}

.skip-choice-item {
  border: 1px solid var(--border-color);
  padding: 12px 16px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.skip-choice-item:hover {
  border-color: var(--submit-button-color);
}

/* Theme-specific hover backgrounds */
.theme-light .skip-choice-item:hover {
  background: rgba(0, 0, 0, 0.05);
}

.theme-dark .skip-choice-item:hover {
  background: rgba(255, 255, 255, 0.05);
}

@media (prefers-color-scheme: light) {
  :root:not(.theme-dark) .skip-choice-item:hover {
    background: rgba(0, 0, 0, 0.05);
  }
}

@media (prefers-color-scheme: dark) {
  :root:not(.theme-light) .skip-choice-item:hover {
    background: rgba(255, 255, 255, 0.05);
  }
}

.choice-text {
  color: var(--text-color);
  font-size: 0.95em;
  line-height: 1.4;
}

.choice-hint {
  margin-top: 8px;
  font-size: 0.85em;
  opacity: 0.7;
  font-style: italic;
  color: var(--text-secondary);
}

.cancel-button {
  background: none;
  border: 1px solid var(--border-color);
  color: var(--text-color);
  padding: 8px 16px;
  font-family: monospace;
  font-size: 0.9em;
  cursor: pointer;
  transition: all 0.2s ease;
  opacity: 0.7;
}

.cancel-button:hover {
  opacity: 1;
  border-color: var(--text-color);
}

/* Bottom spacer to ensure skip button is visible */
.bottom-spacer {
  height: 120px;
  flex-shrink: 0;
}
</style> 
