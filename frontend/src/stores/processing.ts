import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { uploadResume, submitProcessTask, getTaskStatus } from '@/api/resume'
import {
  createJDConversion,
  getJDConversion,
  provideJDConversionLocation,
  type JDConversionTask,
  type JDOutputLanguage
} from '@/api/jd-conversion'
import type { TaskStatus, ProcessingStep, JDContent } from '@/types'

export const useProcessingStore = defineStore('processing', () => {
  // 上传状态
  const uploadedFile = ref<{
    file_id: string
    original_filename: string
    saved_filename: string
    file_size: number
    file_size_display: string
  } | null>(null)
  const uploadProgress = ref(0)
  const isUploading = ref(false)

  // 配置
  const selectedTemplate = ref<string>('')
  const outputLanguage = ref<'zh' | 'en' | 'cnen'>('en')
  const jdText = ref('')
  const jdId = ref('')
  const department = ref('')
  const processingMode = ref<'cv' | 'jd'>('cv')
  const activeTaskMode = ref<'cv' | 'jd' | null>(null)

  // 任务状态
  const currentTaskId = ref<string | null>(null)
  const taskStatus = ref<TaskStatus>('idle')
  const taskProgress = ref(0)
  const taskSteps = ref<ProcessingStep[]>([])
  const taskResult = ref<any>(null)
  const taskError = ref<string | null>(null)
  const isPolling = ref(false)
  const requiredInput = ref<JDConversionTask['required_input']>(null)

  // CV 预览数据（左侧信息面板）
  const previewData = ref<{
    name?: string
    position?: string
    experience?: string
    company?: string
    language?: string
    matchRate?: number
    matchLevel?: string
    skills?: string[]
  } | null>(null)

  // 完整简历结构化数据（右侧预览面板）
  const resumeData = ref<{
    name?: string
    position?: string
    total_exp?: string
    summary?: string
    work?: Array<{ company?: string; period?: string; role?: string; tasks?: string }>
    project?: Array<{ company?: string; period?: string; name?: string; role?: string; tasks?: string }>
    education?: Array<{ period?: string; school?: string; degree?: string; major?: string }>
    tech_skills?: string
    lang_skills?: string
  } | null>(null)
  const jdContent = ref<JDContent | null>(null)

  // 计算属性
  const isProcessing = computed(() => taskStatus.value === 'processing' || taskStatus.value === 'pending')
  const isAwaitingInput = computed(() => taskStatus.value === 'awaiting_input')
  const isCompleted = computed(() => taskStatus.value === 'completed')
  const isFailed = computed(() => taskStatus.value === 'failed')
  const isIdle = computed(() => taskStatus.value === 'idle')

  let pollTimer: ReturnType<typeof setInterval> | null = null

  /** 上传简历文件 */
  async function uploadFile(file: File) {
    isUploading.value = true
    uploadProgress.value = 0
    try {
      const res = await uploadResume(file, (percent) => {
        uploadProgress.value = percent
      })
      uploadedFile.value = res.data
      return res.data
    } finally {
      isUploading.value = false
    }
  }

  /** 提交处理任务 */
  async function submitTask() {
    if (!uploadedFile.value) throw new Error('请先上传简历文件')

    stopPolling()
    activeTaskMode.value = processingMode.value
    taskResult.value = null
    previewData.value = null
    resumeData.value = null
    jdContent.value = null
    requiredInput.value = null
    taskError.value = null

    const res = processingMode.value === 'jd'
      ? await createJDConversion({
          file_id: uploadedFile.value.file_id,
          original_filename: uploadedFile.value.original_filename,
          department: department.value,
          category: 'technical',
          target_position: jdText.value.trim() || undefined,
          target_position_source: jdText.value.trim() ? 'manual' : 'content',
          output_language: toJDOutputLanguage(outputLanguage.value)
        })
      : await submitProcessTask({
          file_id: uploadedFile.value.file_id,
          original_filename: uploadedFile.value.original_filename,
          template_id: selectedTemplate.value || undefined,
          language: outputLanguage.value,
          jd_text: jdText.value || undefined,
          department: department.value
        })

    currentTaskId.value = res.data.task_id
    taskStatus.value = 'pending'
    taskProgress.value = 0
    taskSteps.value = []
    taskError.value = null
    startPolling()
    return res.data.task_id
  }

  /** 开始轮询任务状态 */
  function startPolling() {
    stopPolling()
    isPolling.value = true
    pollTimer = setInterval(async () => {
      if (!currentTaskId.value) {
        stopPolling()
        return
      }
      try {
        if (activeTaskMode.value === 'jd') {
          const res = await getJDConversion(currentTaskId.value)
          applyJDTask(res.data)
          return
        }

        const res = await getTaskStatus(currentTaskId.value)
        taskStatus.value = res.data.status
        taskProgress.value = res.data.progress
        taskSteps.value = (res.data.steps || []) as ProcessingStep[]
        taskError.value = res.data.error_message || res.data.error || null

        if (res.data.status === 'completed') {
          taskResult.value = res.data.result
          // 更新预览数据
          if (res.data.result) {
            previewData.value = {
              name: res.data.result.anonymized_name || res.data.result.name,
              position: res.data.result.position,
              experience: res.data.result.total_exp,
              company: res.data.result.current_company,
              language: outputLanguage.value === 'en' ? 'English' : '中文',
              matchRate: res.data.result.match_rate,
              matchLevel: res.data.result.match_level,
              skills: res.data.result.skills
            }
            // 更新完整简历数据（供右侧预览面板）
            resumeData.value = res.data.result.resume_data || null
          }
          stopPolling()
        } else if (res.data.status === 'failed') {
          stopPolling()
        }
      } catch {
        // 轮询失败时继续尝试
      }
    }, 2000)
  }

  function applyJDTask(task: JDConversionTask) {
    taskStatus.value = task.status
    taskProgress.value = task.progress
    taskSteps.value = task.steps || []
    taskError.value = task.error_message || null
    requiredInput.value = task.required_input || null

    if (task.status === 'awaiting_input') {
      stopPolling()
      return
    }

    if (task.status === 'completed' && task.result) {
      const content = task.result.jd_data
      taskResult.value = task.result
      jdContent.value = content
      previewData.value = {
        name: content.department,
        position: task.result.target_position || content.title_cn || content.title_en,
        language: outputLanguage.value === 'zh'
          ? 'Chinese'
          : outputLanguage.value === 'cnen' ? 'Chinese + English' : 'English'
      }
      stopPolling()
    } else if (task.status === 'failed') {
      stopPolling()
    }
  }

  async function submitRequiredLocation(location: string) {
    if (!currentTaskId.value || activeTaskMode.value !== 'jd') return
    const res = await provideJDConversionLocation(currentTaskId.value, location)
    applyJDTask(res.data)
    if (res.data.status !== 'completed' && res.data.status !== 'failed') startPolling()
  }

  /** 停止轮询 */
  function stopPolling() {
    isPolling.value = false
    if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  }

  /** 重置所有状态 */
  function resetAll() {
    stopPolling()
    uploadedFile.value = null
    uploadProgress.value = 0
    currentTaskId.value = null
    taskStatus.value = 'idle'
    taskProgress.value = 0
    taskSteps.value = []
    taskResult.value = null
    taskError.value = null
    activeTaskMode.value = null
    requiredInput.value = null
    previewData.value = null
    resumeData.value = null
    jdContent.value = null
    department.value = ''
  }

  function toJDOutputLanguage(language: 'zh' | 'en' | 'cnen'): JDOutputLanguage {
    if (language === 'zh') return 'CN'
    if (language === 'cnen') return 'CNEN'
    return 'EN'
  }

  return {
    uploadedFile,
    uploadProgress,
    isUploading,
    selectedTemplate,
    outputLanguage,
    jdText,
    jdId,
    department,
    processingMode,
    activeTaskMode,
    currentTaskId,
    taskStatus,
    taskProgress,
    taskSteps,
    taskResult,
    taskError,
    isPolling,
    requiredInput,
    previewData,
    resumeData,
    jdContent,
    isProcessing,
    isAwaitingInput,
    isCompleted,
    isFailed,
    isIdle,
    uploadFile,
    submitTask,
    submitRequiredLocation,
    startPolling,
    stopPolling,
    resetAll
  }
})
