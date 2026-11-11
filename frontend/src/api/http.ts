import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'
import { i18n, localizeApiMessage } from '@/locales'

declare module 'axios' {
  interface AxiosRequestConfig {
    skipErrorMessage?: boolean
    skipAuthRedirect?: boolean
  }
}

const BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api/v1'

const http: AxiosInstance = axios.create({
  baseURL: BASE_URL,
  withCredentials: true,
  timeout: 120000, // 2分钟超时，处理大文件需要时间
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
http.interceptors.request.use(
  (config) => {
    config.headers.set('Accept-Language', i18n.global.locale.value)
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
http.interceptors.response.use(
  (response: AxiosResponse) => {
    return response.data
  },
  (error) => {
    const message = localizeApiMessage(error.response?.data?.detail || error.message, 'common.networkError')
    const isLoginRequest = error.config?.url?.startsWith('/auth/login')
    if (error.response?.status === 401 && !isLoginRequest && !error.config?.skipAuthRedirect) {
      window.dispatchEvent(new CustomEvent('auth:unauthorized'))
    }
    if (!error.config?.skipErrorMessage) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default http
