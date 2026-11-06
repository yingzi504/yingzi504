import axios from 'axios'
import type { AxiosInstance, AxiosResponse } from 'axios'
import { ElMessage } from 'element-plus'

declare module 'axios' {
  interface AxiosRequestConfig {
    skipErrorMessage?: boolean
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
    // 可在此添加 token 等认证信息
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
    const message = error.response?.data?.detail || error.message || '网络请求失败'
    if (error.response?.status === 401 && !location.pathname.startsWith('/login') && !error.config?.url?.startsWith('/auth/')) {
      location.assign('/login')
    }
    if (!error.config?.skipErrorMessage) {
      ElMessage.error(message)
    }
    return Promise.reject(error)
  }
)

export default http
