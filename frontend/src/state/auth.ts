const AUTH_STORAGE_KEY = 'chefmate-auth-session'

export interface AuthSession {
  token: string
  username: string
  displayName?: string
  email?: string | null
  loggedInAt: string
  hasCompletedWorkspaceOnboarding?: boolean
  profileCompletedAt?: string | null
}

function canUseStorage() {
  return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined'
}

export function getAuthSession(): AuthSession | null {
  if (!canUseStorage()) {
    return null
  }

  const sessionText = window.localStorage.getItem(AUTH_STORAGE_KEY)
  if (!sessionText) {
    return null
  }

  try {
    return JSON.parse(sessionText) as AuthSession
  } catch {
    window.localStorage.removeItem(AUTH_STORAGE_KEY)
    return null
  }
}

export function getAuthToken() {
  return getAuthSession()?.token ?? null
}

export function isAuthenticated() {
  return getAuthSession() !== null
}

export function saveAuthSession(session: AuthSession) {
  if (!canUseStorage()) {
    return
  }

  window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(session))
}

export function updateAuthSession(patch: Partial<AuthSession>) {
  const currentSession = getAuthSession()
  if (!currentSession) {
    return
  }

  saveAuthSession({
    ...currentSession,
    ...patch,
  })
}

export function clearAuthSession() {
  if (!canUseStorage()) {
    return
  }

  window.localStorage.removeItem(AUTH_STORAGE_KEY)
}
