import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getTemplates, uploadTemplate, deleteTemplate, toggleTemplateStatus, updateTemplate } from '@/api/template'
import { adaptTemplate, adaptTemplates, type BackendTemplate } from '@/api/adapters'
import type { TemplateItem } from '@/types'

export const useTemplateStore = defineStore('template', () => {
  const templates = ref<TemplateItem[]>([])
  const isLoading = ref(false)
  const activeCategory = ref<string>('')

  /** 加载模板列表 */
  async function fetchTemplates(category?: string) {
    isLoading.value = true
    try {
      const res = await getTemplates({ category })
      templates.value = adaptTemplates((res.data || []) as unknown as BackendTemplate[])
    } finally {
      isLoading.value = false
    }
  }

  /** 上传新模板 */
  async function addTemplate(file: File, name?: string) {
    const res = await uploadTemplate(file, name)
    const item = adaptTemplate(res.data as unknown as BackendTemplate)
    templates.value.unshift(item)
    return item
  }

  /** 更新模板版本 */
  async function upgradeTemplate(id: string, file: File) {
    const res = await updateTemplate(id, file)
    const item = adaptTemplate(res.data as unknown as BackendTemplate)
    const idx = templates.value.findIndex(t => t.id === id)
    if (idx >= 0) templates.value[idx] = item
    return item
  }

  /** 删除模板 */
  async function removeTemplate(id: string) {
    await deleteTemplate(id)
    templates.value = templates.value.filter(t => t.id !== id)
  }

  /** 切换模板状态 */
  async function toggleStatus(id: string, active: boolean) {
    await toggleTemplateStatus(id, active)
    const t = templates.value.find(t => t.id === id)
    if (t) t.active = active
  }

  return {
    templates,
    isLoading,
    activeCategory,
    fetchTemplates,
    addTemplate,
    upgradeTemplate,
    removeTemplate,
    toggleStatus
  }
})
