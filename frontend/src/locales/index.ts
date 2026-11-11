import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import en from './en'

const storedLang = localStorage.getItem('app-lang')
const savedLang: 'zh-CN' | 'en' = storedLang === 'en' ? 'en' : 'zh-CN'

export const i18n = createI18n({
  legacy: false,
  locale: savedLang,
  fallbackLocale: 'zh-CN',
  messages: {
    'zh-CN': zhCN,
    'en': en
  }
})

export function switchLanguage(lang: 'zh-CN' | 'en') {
  i18n.global.locale.value = lang
  localStorage.setItem('app-lang', lang)
  document.documentElement.lang = lang
}

document.documentElement.lang = savedLang

const apiErrorKeys: Record<string, string> = {
  '请先登录': 'apiErrors.signInRequired',
  '请先修改初始密码': 'apiErrors.changePasswordRequired',
  '需要管理员权限': 'apiErrors.adminRequired',
  '需要超级管理员权限': 'apiErrors.superadminRequired',
  '账号或密码错误，或账号已停用': 'apiErrors.invalidCredentials',
  '登录尝试过多，请在 15 分钟后重试': 'apiErrors.tooManyAttempts',
  '当前密码错误': 'apiErrors.currentPasswordIncorrect',
  '新密码不能与当前密码相同': 'apiErrors.passwordMustDiffer',
  '此账号已存在': 'apiErrors.accountExists',
  '账号不存在': 'apiErrors.accountNotFound',
  '记录不存在或无权访问': 'apiErrors.recordUnavailable',
  '不允许来自此站点的请求': 'apiErrors.originRejected',
  '模型服务余额不足，请联系管理员充值或切换模型后重试': 'apiErrors.llmInsufficientBalance',
  '模型服务认证失败，请联系管理员检查 API 密钥': 'apiErrors.llmAuthenticationFailed',
  '模型服务请求过于频繁，请稍后重试': 'apiErrors.llmRateLimited',
  '模型服务暂时无法连接，请稍后重试': 'apiErrors.llmConnectionFailed',
  '模型返回格式异常，请重新处理；如持续失败请联系管理员': 'apiErrors.llmInvalidResponse',
  '模型服务暂时不可用，请稍后重试或联系管理员': 'apiErrors.llmUnavailable'
}

export function localizeApiMessage(message: unknown, fallbackKey = 'common.requestFailed'): string {
  if (typeof message !== 'string' || !message.trim()) return i18n.global.t(fallbackKey)
  const key = apiErrorKeys[message.trim()]
  if (key) return i18n.global.t(key)
  if (i18n.global.locale.value === 'en' && /[\u3400-\u9fff]/.test(message)) return i18n.global.t(fallbackKey)
  return message
}
