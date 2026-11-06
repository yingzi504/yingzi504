import { createI18n } from 'vue-i18n'
import zhCN from './zh-CN'
import en from './en'

const savedLang = localStorage.getItem('app-lang') || 'zh-CN'

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
}
