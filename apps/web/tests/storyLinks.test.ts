import { describe, expect, it } from 'vitest'
import {
  getPublicDiscoveryPath,
  getPublicStoryPath,
  getStoryRemixPath
} from '../src/lib/storyLinks'

describe('storyLinks', () => {
  it('builds the public discovery path', () => {
    expect(getPublicDiscoveryPath()).toBe('/discover')
  })

  it('builds a public share path', () => {
    expect(getPublicStoryPath('story-123')).toBe('/share/story-123')
  })

  it('builds a remix link with prompt and gender', () => {
    expect(
      getStoryRemixPath({
        user_input: 'A city hanging from a chain above a red ocean.',
        gender_preference: 'female'
      })
    ).toBe(
      '/create?prompt=A+city+hanging+from+a+chain+above+a+red+ocean.&gender=female'
    )
  })
})
