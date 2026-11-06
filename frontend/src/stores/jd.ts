import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getJDs, createJD, updateJD, deleteJD } from '@/api/jd'
import { adaptJD, adaptJDList, type BackendJD } from '@/api/adapters'
import type { JDItem } from '@/types'

export const useJDStore = defineStore('jd', () => {
  const jds = ref<JDItem[]>([])
  const isLoading = ref(false)
  const total = ref(0)
  const activeCategory = ref<string>('')
  const activeLanguage = ref<string>('')
  const keyword = ref('')

  /** 加载JD列表 */
  async function fetchJDs(params?: { category?: string; language?: string; keyword?: string; page?: number; pageSize?: number }) {
    isLoading.value = true
    try {
      const res = await getJDs(params)
      jds.value = adaptJDList((res.data || []) as unknown as BackendJD[])
      total.value = (res as any).total || 0
    } finally {
      isLoading.value = false
    }
  }

  /** 创建JD */
  async function addJD(data: Parameters<typeof createJD>[0]) {
    const res = await createJD(data)
    const item = adaptJD(res.data as unknown as BackendJD)
    jds.value.unshift(item)
    return item
  }

  /** 更新JD */
  async function editJD(id: string, data: Partial<JDItem>) {
    const res = await updateJD(id, data)
    const item = adaptJD(res.data as unknown as BackendJD)
    const idx = jds.value.findIndex(j => j.id === id)
    if (idx >= 0) jds.value[idx] = item
    return item
  }

  /** 删除JD */
  async function removeJD(id: string) {
    await deleteJD(id)
    jds.value = jds.value.filter(j => j.id !== id)
  }

  return {
    jds,
    isLoading,
    total,
    activeCategory,
    activeLanguage,
    keyword,
    fetchJDs,
    addJD,
    editJD,
    removeJD
  }
})
