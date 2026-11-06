// ===== 通用类型 =====

export interface ApiResponse<T = any> {
  success: boolean
  data: T
  message: string
  timestamp: string
}

export interface ApiListResponse<T = any> {
  success: boolean
  data: {
    items: T[]
    total: number
    page: number
    pageSize: number
  }
  message: string
  timestamp: string
}

// ===== 任务相关 =====

export type TaskStatus = 'idle' | 'pending' | 'processing' | 'awaiting_input' | 'completed' | 'failed'

export interface ProcessingStep {
  step?: number
  name: string
  key?: string
  status: 'pending' | 'running' | 'in_progress' | 'done' | 'completed' | 'error' | 'failed' | 'skipped'
  duration?: string | null
  duration_ms?: number
}

// ===== 历史记录 =====

export interface HistoryRecord {
  id: string
  candidateName: string
  targetPosition: string
  language: string
  templateType?: string
  status: 'success' | 'failed' | 'processing'
  matchRate: number
  duration: string
  createdAt: string
  originalFilename?: string
  outputType?: 'cv' | 'jd'
  hasPreview?: boolean
}

export interface Statistics {
  totalCount: number
  successRate: number
  monthlyCount: number
}

// ===== 模板 =====

export interface TemplateItem {
  id: string
  name: string
  version: string
  category: 'portrait' | 'landscape'
  language: string
  updatedAt: string
  active?: boolean
}

// ===== JD =====

export interface JDItem {
  id: string
  position: string
  department: string
  language: string
  category: string
  tags: string[]
  usageCount: number
  updatedAt: string
  active?: boolean
  content?: string
}

export interface BilingualItems {
  cn: string[]
  en: string[]
}

export interface JDRequirements {
  education: BilingualItems
  experience: BilingualItems
  required_skills: BilingualItems
  language: BilingualItems
  preferred: BilingualItems
  soft_skills: BilingualItems
}

export interface JDContent {
  title_cn: string
  title_en: string
  location_cn: string
  location_en: string
  department: string
  category: 'technical' | 'non_technical'
  responsibilities_cn: string[]
  responsibilities_en: string[]
  requirements: JDRequirements
}
