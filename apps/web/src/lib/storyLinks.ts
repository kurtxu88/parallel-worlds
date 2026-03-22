import type { StoryRecord } from './api'
import { resolvePublicUrl } from './site'

type RemixSource = Pick<StoryRecord, 'user_input' | 'gender_preference'>

export function getPublicDiscoveryPath() {
  return '/discover'
}

export function getPublicStoryPath(storyId: string) {
  return `/share/${storyId}`
}

export function getPublicStoryUrl(storyId: string) {
  if (typeof window !== 'undefined' && window.location?.origin) {
    return new URL(getPublicStoryPath(storyId), window.location.origin).toString()
  }

  return resolvePublicUrl(getPublicStoryPath(storyId))
}

export function getStoryRemixPath(source: RemixSource) {
  if (!source.user_input.trim()) {
    return '/create'
  }

  const params = new URLSearchParams({
    prompt: source.user_input,
    gender: source.gender_preference
  })

  return `/create?${params.toString()}`
}
