import { beforeEach, describe, expect, it, vi } from 'vitest'

vi.mock('../src/lib/api', () => ({
  createGuestSession: vi.fn()
}))

import { createGuestSession } from '../src/lib/api'
import { ensureGuestUser, getGuestUserId } from '../src/lib/guestSession'

describe('guest session helper', () => {
  let store: Record<string, string>

  beforeEach(() => {
    store = {}
    const storage = {
      getItem: (key: string) => store[key] ?? null,
      setItem: (key: string, value: string) => {
        store[key] = value
      },
      removeItem: (key: string) => {
        delete store[key]
      },
      clear: () => {
        store = {}
      }
    }

    Object.defineProperty(window, 'localStorage', {
      value: storage,
      configurable: true
    })

    Object.defineProperty(globalThis, 'localStorage', {
      value: storage,
      configurable: true
    })

    vi.mocked(createGuestSession).mockReset()
  })

  it('creates and stores a guest id when none exists', async () => {
    vi.mocked(createGuestSession).mockResolvedValue({ user_id: 'guest-123' })

    const userId = await ensureGuestUser()

    expect(userId).toBe('guest-123')
    expect(getGuestUserId()).toBe('guest-123')
    expect(createGuestSession).toHaveBeenCalledTimes(1)
  })

  it('reuses the cached guest id', async () => {
    window.localStorage.setItem('parallel_worlds_guest_user_id', 'guest-cached')

    const userId = await ensureGuestUser()

    expect(userId).toBe('guest-cached')
    expect(createGuestSession).not.toHaveBeenCalled()
  })
})
