import http from './http'
import type { ApiResponse, JDContent, ProcessingStep, TaskStatus } from '@/types'

export type JDOutputLanguage = 'CN' | 'EN' | 'CNEN'
export type JDTargetPositionSource = 'manual' | 'filename' | 'content'
export type JDPositionRecognitionSource = Exclude<JDTargetPositionSource, 'manual'>

export interface JDPositionRecognitionResult {
  target_position: string
  target_position_source: JDPositionRecognitionSource
}

export interface JDConversionResult {
  task_id: string
  output_filename: string
  docx_download_url: string
  pdf_download_url?: string | null
  pdf_available: boolean
  jd_data: JDContent
  target_position: string
  target_position_source: JDTargetPositionSource
  generation_mode: 'full_jd' | 'partial_jd' | 'title_only'
}

export interface JDConversionTask {
  task_id: string
  status: Exclude<TaskStatus, 'idle'>
  progress: number
  current_step: string
  steps: ProcessingStep[]
  error_message?: string | null
  required_input?: {
    field: 'location'
    reason: 'missing_source_location'
  } | null
  result?: JDConversionResult | null
}

export function createJDConversion(params: {
  file_id?: string
  original_filename?: string
  source_text?: string
  department?: string
  category: 'technical' | 'non_technical'
  target_position?: string
  target_position_source: JDTargetPositionSource
  output_language: JDOutputLanguage
}): Promise<ApiResponse<JDConversionTask>> {
  return http.post('/jd-conversion/tasks', params)
}

export function recognizeJDPosition(params: {
  file_id?: string
  original_filename?: string
  source_text?: string
  target_position_source: JDPositionRecognitionSource
  output_language: JDOutputLanguage
}): Promise<ApiResponse<JDPositionRecognitionResult>> {
  return http.post('/jd-conversion/recognize-position', params, { skipErrorMessage: true })
}

export function getJDConversion(taskId: string): Promise<ApiResponse<JDConversionTask>> {
  return http.get(`/jd-conversion/tasks/${taskId}`)
}

export function regenerateJDConversion(
  taskId: string,
  content: JDContent
): Promise<ApiResponse<JDConversionTask>> {
  return http.put(`/jd-conversion/tasks/${taskId}`, { content })
}

export function provideJDConversionLocation(
  taskId: string,
  location: string
): Promise<ApiResponse<JDConversionTask>> {
  return http.post(`/jd-conversion/tasks/${taskId}/location`, { location })
}

export function downloadJDConversion(taskId: string, format: 'docx' | 'pdf'): Promise<Blob> {
  return http.get(`/jd-conversion/tasks/${taskId}/download`, {
    params: { format },
    responseType: 'blob'
  })
}

export function saveJDConversion(taskId: string): Promise<ApiResponse<unknown>> {
  return http.post(`/jd-conversion/tasks/${taskId}/save`)
}
