import { ref } from 'vue'
import http from '@/api/http'

export interface Account {
  id: number
  email: string
  role: 'admin' | 'member'
  account_type: string
  permissions: string[]
  active: boolean
  must_change_password: boolean
}

export const account = ref<Account | null>(null)
export function canUse(feature: string) {
  return account.value?.role === 'admin' || !!account.value?.permissions.includes(feature)
}
export async function refreshAccount() {
  try {
    const result: any = await http.get('/auth/me', { skipErrorMessage: true })
    account.value = result.data
  } catch (error: any) {
    if (error.response?.status === 401) account.value = null
    else throw error
  }
  return account.value
}
export async function signOut() {
  await http.post('/auth/logout')
  account.value = null
  // Drop all task previews and polling state when changing users.
  location.assign('/login')
}
