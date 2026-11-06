import http from './http'
import type { HistoryRecord, Statistics, ApiResponse, ApiListResponse } from '@/types'

/** 获取历史记录列表 */
export function getHistoryList(params?: {
  status?: string
  language?: string
  output_type?: 'cv' | 'jd'
  keyword?: string
  page?: number
  pageSize?: number
}): Promise<ApiListResponse<HistoryRecord>> {
  return http.get('/history/list', { params })
}

/** 获取历史记录详情 */
export function getHistoryDetail(id: string): Promise<ApiResponse<HistoryRecord>> {
  return http.get(`/history/${id}`)
}

/** 获取统计数据 */
export function getStatistics(): Promise<ApiResponse<Statistics>> {
  return http.get('/history/statistics')
}

/** 删除历史记录 */
export function deleteHistory(id: string): Promise<ApiResponse<null>> {
  return http.delete(`/history/${id}`)
}
