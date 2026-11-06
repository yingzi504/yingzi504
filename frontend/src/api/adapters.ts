/**
 * ============================================================
 * API 响应适配层 (Adapter Layer)
 * ============================================================
 *
 * 目的：将后端 API 的实际返回格式转换为前端组件期望的类型。
 * 当后端字段名、枚举值或数据结构发生变化时，只需修改此文件，
 * 前端所有页面组件和 Store 无需任何改动。
 *
 * 使用方式：
 *   import { adaptTemplate, adaptTemplates, adaptJD, ... } from '@/api/adapters'
 *   const templates = adaptTemplates(backendResponse.data)
 */

import type { TemplateItem, HistoryRecord, Statistics, JDItem } from '@/types'

// ============================================================
// 后端原始返回类型定义
// ============================================================

/** 后端模板列表项 */
export interface BackendTemplate {
  id: string
  name: string
  category: 'vertical' | 'horizontal'    // 后端枚举
  version: string
  updateTime: string                     // 后端字段名
  filePath: string
  status: 'active' | 'inactive'          // 后端枚举
}

/** 后端历史记录项 */
export interface BackendHistoryItem {
  id: string
  timestamp: string
  originalFile: string
  fileSize: string
  jobPosition: string
  language: string
  template: string
  jdMatchScore?: number
  status: 'completed' | 'failed'
  processingTime: string
  outputFile: string
}

/** 后端统计信息 */
export interface BackendStatistics {
  total: number
  successRate: number
  monthly: number
}

/** 后端 JD 项 */
export interface BackendJD {
  id: string
  title: string
  department?: string
  category: string
  language: string
  isHot: boolean
  active?: boolean
  tags?: string[]
  description: string
  structuredData?: unknown
  createTime: string
  usageCount: number
  lastUsed: string
}

// ============================================================
// 适配函数：Backend → Frontend
// ============================================================

/** 适配单个模板 */
export function adaptTemplate(raw: BackendTemplate): TemplateItem {
  return {
    id: raw.id,
    name: raw.name,
    version: raw.version,
    category: raw.category === 'vertical' ? 'portrait' : 'landscape',
    language: inferLanguage(raw.name),
    updatedAt: raw.updateTime,
    active: raw.status === 'active',
  }
}

/** 适配模板列表 */
export function adaptTemplates(rawList: BackendTemplate[]): TemplateItem[] {
  return rawList.map(adaptTemplate)
}

/** 从文件名提取显示名称（去掉扩展名） */
function displayNameFromFilename(filename: string): string {
  return filename.replace(/\.[^.]+$/, '')
}

/** 适配单个历史记录 */
export function adaptHistoryItem(raw: BackendHistoryItem): HistoryRecord {
  return {
    id: raw.id,
    candidateName: displayNameFromFilename(raw.originalFile),
    originalFilename: raw.originalFile,
    targetPosition: raw.jobPosition,
    language: raw.language,
    templateType: raw.template,
    status: raw.status === 'completed' ? 'success' : 'failed',
    matchRate: raw.jdMatchScore ?? 0,
    duration: raw.processingTime,
    createdAt: raw.timestamp,
  }
}

/** 适配历史记录列表 */
export function adaptHistoryList(rawList: BackendHistoryItem[]): HistoryRecord[] {
  return rawList.map(adaptHistoryItem)
}

/** 适配统计信息 */
export function adaptStatistics(raw: BackendStatistics): Statistics {
  return {
    totalCount: raw.total,
    successRate: raw.successRate,
    monthlyCount: raw.monthly,
  }
}

/** 适配单个 JD */
export function adaptJD(raw: BackendJD): JDItem {
  return {
    id: raw.id,
    position: raw.title,
    department: raw.department || extractDepartment(raw.title, raw.category),
    language: raw.language,
    category: raw.category,
    tags: raw.tags?.length ? raw.tags : [raw.category],
    usageCount: raw.usageCount,
    updatedAt: raw.lastUsed || raw.createTime,
    active: raw.active !== false,
    content: raw.description,
  }
}

/** 适配 JD 列表 */
export function adaptJDList(rawList: BackendJD[]): JDItem[] {
  return rawList.map(adaptJD)
}

// ============================================================
// 辅助函数
// ============================================================

/** 从模板名称推断语言 */
function inferLanguage(name: string): string {
  const upper = name.toUpperCase()
  if (upper.includes('_EN') || upper.includes('ENGLISH')) return 'EN'
  if (upper.includes('_CN') || upper.includes('CHINESE') || upper.includes('中文')) return 'CN'
  return 'EN' // 默认
}

/** 从 JD 标题/分类提取部门 */
function extractDepartment(_title: string, category: string): string {
  const deptMap: Record<string, string> = {
    '汽车技术': '汽车技术部',
    '产品管理': '产品管理部',
    '软件研发': '软件研发部',
  }
  return deptMap[category] || category
}
