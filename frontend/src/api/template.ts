import http from './http'
import type { TemplateItem, ApiResponse } from '@/types'

/** 获取模板列表 */
export function getTemplates(params?: {
  category?: string
  language?: string
}): Promise<ApiResponse<TemplateItem[]>> {
  return http.get('/template/list', { params })
}

/** 获取模板详情 */
export function getTemplateDetail(id: string): Promise<ApiResponse<TemplateItem>> {
  return http.get(`/template/${id}`)
}

/** 上传新模板 */
export function uploadTemplate(file: File, name?: string): Promise<ApiResponse<TemplateItem>> {
  const formData = new FormData()
  formData.append('file', file)
  if (name) formData.append('name', name)
  return http.post('/template/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/** 更新模板版本 */
export function updateTemplate(id: string, file: File): Promise<ApiResponse<TemplateItem>> {
  const formData = new FormData()
  formData.append('file', file)
  return http.put(`/template/${id}`, formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  })
}

/** 删除模板 */
export function deleteTemplate(id: string): Promise<ApiResponse<null>> {
  return http.delete(`/template/${id}`)
}

/** 切换模板状态 */
export function toggleTemplateStatus(id: string, active: boolean): Promise<ApiResponse<null>> {
  return http.put(`/template/${id}/status`, { active })
}
