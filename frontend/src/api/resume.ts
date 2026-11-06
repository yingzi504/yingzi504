import http from './http'
import type { ApiResponse } from '@/types'

type FrontLanguage = 'zh' | 'en' | 'cnen'
type BackendLanguage = 'CN' | 'EN'
type BackendTemplateType = 'vertical' | 'horizontal'

function toBackendLanguage(language: FrontLanguage): BackendLanguage {
  return language === 'zh' ? 'CN' : 'EN'
}

function toBackendTemplateType(template?: string): BackendTemplateType {
  const value = (template || '').toLowerCase().trim()

  if (!value || value === 'portrait' || value === 'vertical' || value.startsWith('new_')) {
    return 'vertical'
  }

  if (value === 'landscape' || value === 'horizontal' || value.startsWith('onepager_')) {
    return 'horizontal'
  }

  return 'vertical'
}

function toJobPosition(input?: string): string {
  if (!input) return ''
  const firstLine = input.split(/\r?\n/).find(Boolean)?.trim() || ''
  return firstLine.slice(0, 100)
}

/** 上传简历文件 */
export function uploadResume(file: File, onProgress?: (percent: number) => void): Promise<ApiResponse<{
  file_id: string
  original_filename: string
  saved_filename: string
  file_size: number
  file_size_display: string
}>> {
  const formData = new FormData()
  formData.append('file', file)
  return http.post('/resume/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    onUploadProgress: (e) => {
      if (e.total && onProgress) {
        onProgress(Math.round((e.loaded * 100) / e.total))
      }
    }
  })
}

/** 提交处理任务（字段名映射到后端 PipelineSubmitRequest） */
export function submitProcessTask(params: {
  file_id: string
  original_filename?: string
  template_id?: string
  language: FrontLanguage
  jd_text?: string
  target_position?: string
  template_language?: FrontLanguage
  jd_id?: string
  department: string
  mode?: 'cv' | 'jd'
}): Promise<ApiResponse<{ task_id: string }>> {
  const targetLanguage = toBackendLanguage(params.language)
  const templateLanguage = params.template_language
    ? toBackendLanguage(params.template_language)
    : targetLanguage

  return http.post('/process', {
    file_id: params.file_id,
    original_filename: params.original_filename || '',
    template_type: toBackendTemplateType(params.template_id),
    target_language: targetLanguage,
    template_language: templateLanguage,
    job_position: toJobPosition(params.target_position),
    department: params.department,
  })
}

/** 查询任务状态 */
export function getTaskStatus(taskId: string): Promise<ApiResponse<{
  task_id: string
  status: 'pending' | 'processing' | 'awaiting_input' | 'completed' | 'failed'
  required_input?: { field: 'gender'; reason: string } | null
  progress: number
  steps: Array<{ name: string; status: string; duration_ms?: number }>
  result?: any
  error?: string
  error_message?: string
  message?: string
}>> {
  return http.get(`/process/${taskId}`)
}

/** 获取任务结果 */
export function provideCVGender(taskId: string, gender: 'male' | 'female') {
  return http.post(`/process/${taskId}/gender`, { gender })
}

export function getTaskResult(taskId: string): Promise<ApiResponse<any>> {
  return http.get(`/process/${taskId}/result`)
}

/** 下载输出文件 */
export function downloadOutput(taskId: string, format: 'pptx' | 'pdf' | 'docx' = 'pptx'): Promise<Blob> {
  return http.get(`/process/${taskId}/download`, {
    params: { format },
    responseType: 'blob'
  })
}
