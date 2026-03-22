import { createGuestSession } from './api'

const GUEST_USER_STORAGE_KEY = 'parallel_worlds_guest_user_id'

export function getGuestUserId() {
  return localStorage.getItem(GUEST_USER_STORAGE_KEY)
}

export async function ensureGuestUser() {
  const existing = getGuestUserId()
  if (existing) {
    return existing
  }

  const session = await createGuestSession()
  localStorage.setItem(GUEST_USER_STORAGE_KEY, session.user_id)
  return session.user_id
}
