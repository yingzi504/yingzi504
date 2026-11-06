import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getHistoryList, getStatistics, deleteHistory } from '@/api/history'
import { adaptHistoryList, adaptStatistics, type BackendHistoryItem, type BackendStatistics } from '@/api/adapters'
import type { HistoryRecord, Statistics } from '@/types'

export const useHistoryStore = defineStore('history', () => {
  const records = ref<HistoryRecord[]>([])
  const statistics = ref<Statistics | null>(null)
  const isLoading = ref(false)
  const total = ref(0)

  // 筛选条件
  const filterStatus = ref<string>('')
  const filterLanguage = ref<string>('')
  const filterOutputType = ref<string>('')
  const filterKeyword = ref('')
  const currentPage = ref(1)
  const pageSize = ref(10)

  /** 加载历史记录 */
  async function fetchRecords(params?: {
    status?: string
    language?: string
    output_type?: 'cv' | 'jd'
    keyword?: string
    page?: number
    pageSize?: number
  }) {
    isLoading.value = true
    try {
      const res = await getHistoryList(params)
      records.value = adaptHistoryList((res.data || []) as unknown as BackendHistoryItem[])
      total.value = (res as any).total || 0
    } finally {
      isLoading.value = false
    }
  }

  /** 加载统计数据 */
  async function fetchStatistics() {
    const res = await getStatistics()
    statistics.value = adaptStatistics(res.data as unknown as BackendStatistics)
  }

  /** 删除记录 */
  async function removeRecord(id: string) {
    await deleteHistory(id)
    records.value = records.value.filter(r => r.id !== id)
  }

  return {
    records,
    statistics,
    isLoading,
    total,
    filterStatus,
    filterLanguage,
    filterOutputType,
    filterKeyword,
    currentPage,
    pageSize,
    fetchRecords,
    fetchStatistics,
    removeRecord
  }
})
