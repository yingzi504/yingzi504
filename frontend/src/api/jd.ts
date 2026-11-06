import http from './http'
import type { JDItem, ApiResponse, ApiListResponse } from '@/types'

/** 获取JD列表 */
export function getJDs(params?: {
  category?: string
  language?: string
  keyword?: string
  page?: number
  pageSize?: number
}): Promise<ApiListResponse<JDItem>> {
  return http.get('/jd/list', { params })
}

/** 获取JD详情 */
export function getJDDetail(id: string): Promise<ApiResponse<JDItem>> {
  return http.get(`/jd/${id}`)
}

/** 创建新JD */
export function createJD(data: {
  position: string
  department: string
  language: string
  category: string
  content: string
  tags?: string[]
}): Promise<ApiResponse<JDItem>> {
  return http.post('/jd/create', data)
}

/** 更新JD */
export function updateJD(id: string, data: Partial<JDItem>): Promise<ApiResponse<JDItem>> {
  return http.put(`/jd/${id}`, data)
}

/** 删除JD */
export function deleteJD(id: string): Promise<ApiResponse<null>> {
  return http.delete(`/jd/${id}`)
}
