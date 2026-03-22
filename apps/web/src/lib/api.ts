export type AppLanguage = 'en-US' | 'zh-CN'
export type AppTheme = 'system' | 'light' | 'dark'

export interface GuestSession {
  user_id: string
}

export interface StoryRecord {
  id: string
  story_id: string
  user_id: string
  story_title: string | null
  user_input: string
  gender_preference: 'male' | 'female'
  culture_language: AppLanguage
  is_public: boolean
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'error'
  error_message: string | null
  created_at: string
  updated_at: string
  last_entered_at?: string | null
}

export interface StoryEvent {
  id: string
  user_id: string
  story_id: string
  session_id: string
  scene_id?: string | null
  episode_number?: number | null
  round_number?: number | null
  event_type: string
  content: string
  created_at: string
}

export interface PublicStoryRecord {
  id: string
  story_id: string
  story_title: string | null
  user_input: string
  gender_preference: 'male' | 'female'
  culture_language: AppLanguage
  is_public: boolean
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'error'
  error_message: string | null
  created_at: string
  updated_at: string
  last_entered_at?: string | null
}

export interface PublicStorySummary {
  id: string
  story_id: string
  story_title: string | null
  user_input: string
  gender_preference: 'male' | 'female'
  culture_language: AppLanguage
  is_public: boolean
  status: 'pending' | 'generating' | 'completed' | 'failed' | 'error'
  error_message: string | null
  created_at: string
  updated_at: string
  last_entered_at?: string | null
  event_count: number
  preview_excerpt: string | null
}

export interface PublicStoryEvent {
  id: string
  story_id: string
  scene_id?: string | null
  episode_number?: number | null
  round_number?: number | null
  event_type: string
  content: string
  created_at: string
}

export interface UserSettings {
  user_id: string
  language: AppLanguage
  theme: AppTheme
  created_at: string
  updated_at: string
}

export interface StoryCreatePayload {
  user_input: string
  gender_preference: 'male' | 'female'
  culture_language: AppLanguage
  is_public: boolean
}

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

async function apiFetch<T>(path: string, init: RequestInit = {}, userId?: string): Promise<T> {
  const headers = new Headers(init.headers || {})
  if (init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }
  if (userId) {
    headers.set('X-User-Id', userId)
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers
  })

  if (!response.ok) {
    let message = `Request failed: ${response.status}`
    try {
      const payload = await response.json()
      if (payload?.detail) {
        message = payload.detail
      }
    } catch {
      // Ignore JSON parsing failures and use the generic message.
    }
    throw new Error(message)
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

export function getApiBaseUrl() {
  return API_BASE_URL
}

export function createGuestSession() {
  return apiFetch<GuestSession>('/api/session/guest', { method: 'POST' })
}

export function getSettings(userId: string) {
  return apiFetch<UserSettings>('/api/settings', {}, userId)
}

export function updateSettings(
  userId: string,
  payload: Partial<Pick<UserSettings, 'language' | 'theme'>>
) {
  return apiFetch<UserSettings>(
    '/api/settings',
    {
      method: 'PUT',
      body: JSON.stringify(payload)
    },
    userId
  )
}

export function getStories(userId: string) {
  return apiFetch<StoryRecord[]>('/api/stories', {}, userId)
}

export function createStory(userId: string, payload: StoryCreatePayload) {
  return apiFetch<StoryRecord>(
    '/api/stories',
    {
      method: 'POST',
      body: JSON.stringify(payload)
    },
    userId
  )
}

export function getStory(userId: string, storyId: string) {
  return apiFetch<StoryRecord>(`/api/stories/${storyId}`, {}, userId)
}

export function retryStory(userId: string, storyId: string) {
  return apiFetch<StoryRecord>(
    `/api/stories/${storyId}/retry`,
    {
      method: 'POST'
    },
    userId
  )
}

export function getStoryEvents(userId: string, storyId: string) {
  return apiFetch<StoryEvent[]>(`/api/stories/${storyId}/events`, {}, userId)
}

export function updateStoryVisibility(userId: string, storyId: string, isPublic: boolean) {
  return apiFetch<StoryRecord>(
    `/api/stories/${storyId}/visibility`,
    {
      method: 'PATCH',
      body: JSON.stringify({ is_public: isPublic })
    },
    userId
  )
}

export function getPublicStory(storyId: string) {
  return apiFetch<PublicStoryRecord>(`/api/public/stories/${storyId}`)
}

export function getPublicStories(limit = 24) {
  return apiFetch<PublicStorySummary[]>(`/api/public/stories?limit=${limit}`)
}

export function getPublicStoryEvents(storyId: string) {
  return apiFetch<PublicStoryEvent[]>(`/api/public/stories/${storyId}/events`)
}
