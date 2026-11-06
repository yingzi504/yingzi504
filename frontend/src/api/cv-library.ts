import http from './http'

export interface CVLibraryFile {
  format: 'pptx' | 'pdf'
  name: string
  available: boolean
}

export interface CVLibraryItem {
  id: string
  name: string
  department: string
  position: string
  status: string
  created_at: string
  updated_at: string
  files: CVLibraryFile[]
}

export interface DepartmentCount {
  code: string
  count: number
}

export interface CVLibraryResponse {
  success: boolean
  total: number
  page: number
  pageSize: number
  departments: DepartmentCount[]
  unclassified: number
  data: CVLibraryItem[]
}

export function getCVLibrary(params: {
  department?: string
  position?: string
  page?: number
  page_size?: number
}): Promise<CVLibraryResponse> {
  return http.get('/cv-library', { params })
}

export function downloadCVLibraryFile(id: string, format: 'pptx' | 'pdf'): Promise<Blob> {
  return http.get(`/records/${id}/download`, { params: { format }, responseType: 'blob' })
}
