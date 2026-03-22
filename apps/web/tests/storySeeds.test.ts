import { describe, expect, it } from 'vitest'
import { getStorySeedExamples } from '../src/lib/storySeeds'

describe('getStorySeedExamples', () => {
  it('returns starter seeds for English', () => {
    const examples = getStorySeedExamples('en-US')

    expect(examples).toHaveLength(3)
    expect(examples.every(example => example.payload.culture_language === 'en-US')).toBe(true)
  })

  it('returns starter seeds for Chinese', () => {
    const examples = getStorySeedExamples('zh-CN')

    expect(examples).toHaveLength(3)
    expect(examples.every(example => example.payload.culture_language === 'zh-CN')).toBe(true)
  })
})
