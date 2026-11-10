import { ref } from 'vue'
import http from '@/api/http'

export interface Account {
  id: number
  email: string
  role: 'superadmin' | 'admin' | 'member'
  account_type: string
  permissions: string[]
  active: boolean
  must_change_password: boolean
  auth_version: number
}

export const account = ref<Account | null>(null)
const LOGOUT_STORAGE_KEY = 'resume-auth-forced-logout'
const SESSION_CHECK_MS = 15_000
let monitorStarted = false
let checking = false
let channel: BroadcastChannel | null = null

function loginLocation(reason: string) {
  return `/login?reason=${encodeURIComponent(reason)}`
}

export function forceSignOut(reason = 'permissions-changed', notifyPeers = true) {
  account.value = null
  if (notifyPeers) {
    channel?.postMessage({ type: 'logout', reason })
    localStorage.setItem(LOGOUT_STORAGE_KEY, JSON.stringify({ reason, at: Date.now() }))
  }
  if (!location.pathname.startsWith('/login')) location.replace(loginLocation(reason))
}
export function canUse(feature: string) {
  return account.value?.role === 'superadmin' || account.value?.role === 'admin' || !!account.value?.permissions.includes(feature)
}
export async function refreshAccount() {
  const previous = account.value
  try {
    const result: any = await http.get('/auth/me', { skipErrorMessage: true, skipAuthRedirect: true })
    if (previous && (previous.id !== result.data.id || previous.auth_version !== result.data.auth_version)) {
      forceSignOut('permissions-changed')
      return null
    }
    account.value = result.data
  } catch (error: any) {
    if (error.response?.status === 401) {
      account.value = null
      if (previous) forceSignOut('permissions-changed')
    }
    else throw error
  }
  return account.value
}
async function verifySession() {
  if (!account.value || checking || location.pathname.startsWith('/login')) return
  checking = true
  try { await refreshAccount() } finally { checking = false }
}
export function startSessionMonitoring() {
  if (monitorStarted) return
  monitorStarted = true
  if ('BroadcastChannel' in window) {
    channel = new BroadcastChannel('resume-auth')
    channel.addEventListener('message', event => {
      if (event.data?.type === 'logout') forceSignOut(event.data.reason, false)
    })
  }
  window.addEventListener('auth:unauthorized', () => forceSignOut('permissions-changed'))
  window.addEventListener('storage', event => {
    if (event.key === LOGOUT_STORAGE_KEY && event.newValue) {
      try { forceSignOut(JSON.parse(event.newValue).reason || 'permissions-changed', false) }
      catch { forceSignOut('permissions-changed', false) }
    }
  })
  window.addEventListener('focus', () => void verifySession())
  document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible') void verifySession()
  })
  window.setInterval(() => void verifySession(), SESSION_CHECK_MS)
}
export async function signOut() {
  await http.post('/auth/logout')
  account.value = null
  // Drop all task previews and polling state when changing users.
  channel?.postMessage({ type: 'logout', reason: 'signed-out' })
  localStorage.setItem(LOGOUT_STORAGE_KEY, JSON.stringify({ reason: 'signed-out', at: Date.now() }))
  location.replace('/login')
}
