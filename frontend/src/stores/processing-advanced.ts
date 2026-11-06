import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { uploadResume, submitProcessTask, getTaskStatus, provideCVGender } from '@/api/resume'
import {
  createJDConversion,
  getJDConversion,
  provideJDConversionLocation,
  recognizeJDPosition,
  regenerateJDConversion,
  saveJDConversion
} from '@/api/jd-conversion'
import { i18n } from '@/locales'
import type { JDContent, TaskStatus, ProcessingStep } from '@/types'
import type { JDPositionRecognitionSource, JDTargetPositionSource, JDConversionTask } from '@/api/jd-conversion'

export const useProcessingStore = defineStore('processing', () => {
  const uploadedFile = ref<{
    file_id: string
    original_filename: string
    saved_filename: string
    file_size: number
    file_size_display: string
  } | null>(null)
  const uploadProgress = ref(0)
  const isUploading = ref(false)

  const selectedTemplate = ref<string>('portrait')
  const outputLanguage = ref<'' | 'zh' | 'en' | 'cnen'>('zh')
  const jdText = ref('')
  const jdId = ref('')
  const jdSourceMode = ref<'file' | 'text'>('file')
  const jdSourceText = ref('')
  const jdCategory = ref<'technical' | 'non_technical'>('technical')
  const department = ref('')
  const jdTargetPositionSource = ref<JDTargetPositionSource>('content')
  const detectedTargetPosition = ref('')
  const isDetectingTargetPosition = ref(false)
  const targetPositionDetectionError = ref<string | null>(null)
  const jdGenerationMode = ref<'full_jd' | 'partial_jd' | 'title_only' | ''>('')
  const targetPosition = ref('')
  const processingMode = ref<'' | 'cv' | 'jd'>('cv')

  const currentTaskId = ref<string | null>(null)
  const taskStatus = ref<TaskStatus>('idle')
  const taskProgress = ref(0)
  const taskSteps = ref<ProcessingStep[]>([])
  const taskResult = ref<any>(null)
  const taskError = ref<string | null>(null)
  const taskMessage = ref('')
  const requiredInput = ref<JDConversionTask['required_input'] | { field: 'gender'; reason: string }>(null)
  const isPolling = ref(false)

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
  const jdData = ref<JDContent | null>(null)

  const isProcessing = computed(() => taskStatus.value === 'processing' || taskStatus.value === 'pending')
  const isAwaitingInput = computed(() => taskStatus.value === 'awaiting_input')
  const isCompleted = computed(() => taskStatus.value === 'completed')
  const isFailed = computed(() => taskStatus.value === 'failed')
  const isIdle = computed(() => taskStatus.value === 'idle')

  function detectTargetPositionLanguage(value: string): 'zh' | 'en' | null {
    const text = value.trim()
    if (!text) return null
    if (/[\u3400-\u9fff]/.test(text)) return 'zh'
    if (/[A-Za-z]/.test(text)) return 'en'
    return null
  }

  function getTargetPositionLanguageMismatch() {
    if (processingMode.value === 'jd') return null
    const positionLanguage = detectTargetPositionLanguage(targetPosition.value)
    if (!positionLanguage || outputLanguage.value === 'cnen' || !outputLanguage.value) return null
    if (positionLanguage === outputLanguage.value) return null
    return { positionLanguage, outputLanguage: outputLanguage.value }
  }

  let pollTimer: ReturnType<typeof setInterval> | null = null
  let targetPositionRecognitionRequestId = 0

  function jdOutputLanguage() {
    return outputLanguage.value === 'en' ? 'EN' : outputLanguage.value === 'cnen' ? 'CNEN' : 'CN'
  }

  function resetTargetPositionRecognition(clearTargetPosition = true) {
    targetPositionRecognitionRequestId += 1
    isDetectingTargetPosition.value = false
    targetPositionDetectionError.value = null
    detectedTargetPosition.value = ''
    if (clearTargetPosition) targetPosition.value = ''
  }

  async function recognizeTargetPosition(source: JDPositionRecognitionSource): Promise<string> {
    const hasFile = jdSourceMode.value === 'file' && !!uploadedFile.value
    const hasText = jdSourceMode.value === 'text' && !!jdSourceText.value.trim()
    if (source === 'filename' && !hasFile) {
      throw new Error(i18n.global.t('upload.pleaseUploadForFilename'))
    }
    if (source === 'content' && !(hasFile || hasText)) {
      throw new Error(i18n.global.t('upload.pleaseProvideJDSource'))
    }

    const requestId = ++targetPositionRecognitionRequestId
    jdTargetPositionSource.value = source
    isDetectingTargetPosition.value = true
    targetPositionDetectionError.value = null
    detectedTargetPosition.value = ''
    targetPosition.value = ''

    try {
      const res = await recognizeJDPosition({
        file_id: jdSourceMode.value === 'file' ? uploadedFile.value?.file_id : undefined,
        original_filename: jdSourceMode.value === 'file' ? uploadedFile.value?.original_filename : undefined,
        source_text: jdSourceMode.value === 'text' ? jdSourceText.value.trim() : undefined,
        target_position_source: source,
        output_language: jdOutputLanguage()
      })
      if (requestId !== targetPositionRecognitionRequestId) return ''
      const position = res.data.target_position.trim()
      if (!position) throw new Error(i18n.global.t('upload.positionRecognitionFailed'))
      detectedTargetPosition.value = position
      targetPosition.value = position
      return position
    } catch (error) {
      if (requestId !== targetPositionRecognitionRequestId) return ''
      targetPositionDetectionError.value = error instanceof Error ? error.message : 'recognition_failed'
      throw error
    } finally {
      if (requestId === targetPositionRecognitionRequestId) {
        isDetectingTargetPosition.value = false
      }
    }
  }

  async function uploadFile(file: File) {
    isUploading.value = true
    uploadProgress.value = 0
    try {
      const res = await uploadResume(file, percent => { uploadProgress.value = percent })
      uploadedFile.value = res.data
      return res.data
    } finally {
      isUploading.value = false
    }
  }

  async function submitTask() {
    if (!processingMode.value) throw new Error(i18n.global.t('upload.pleaseSelectMode'))
    if (processingMode.value === 'cv' && !uploadedFile.value) {
      throw new Error(i18n.global.t('common.pleaseUploadFirst'))
    }
    if (processingMode.value === 'jd') {
      const hasFile = jdSourceMode.value === 'file' && !!uploadedFile.value
      const hasText = jdSourceMode.value === 'text' && !!jdSourceText.value.trim()
      if (!targetPosition.value.trim()) {
        throw new Error(i18n.global.t('upload.pleaseFillTargetJob'))
      }
      if (jdTargetPositionSource.value === 'filename' && !hasFile) {
        throw new Error(i18n.global.t('upload.pleaseUploadForFilename'))
      }
      if (jdTargetPositionSource.value === 'content' && !(hasFile || hasText)) {
        throw new Error(i18n.global.t('upload.pleaseProvideJDSource'))
      }
    }
    if (processingMode.value === 'cv' && !selectedTemplate.value) {
      throw new Error(i18n.global.t('upload.pleaseSelectTemplate'))
    }
    if (processingMode.value === 'cv' && !department.value.trim()) {
      throw new Error(i18n.global.t('upload.pleaseFillDepartment'))
    }
    if (processingMode.value === 'cv' && getTargetPositionLanguageMismatch()) {
      throw new Error(i18n.global.t('upload.targetPositionLanguageMismatch'))
    }
    const language = outputLanguage.value
    if (!language) throw new Error(i18n.global.t('upload.pleaseSelectOutputLanguage'))

    stopPolling()
    taskResult.value = null
    previewData.value = null
    resumeData.value = null
    jdData.value = null
    taskError.value = null
    requiredInput.value = null

    const res = processingMode.value === 'jd'
      ? await createJDConversion({
          file_id: jdSourceMode.value === 'file' ? uploadedFile.value?.file_id : undefined,
          original_filename: jdSourceMode.value === 'file' ? uploadedFile.value?.original_filename : undefined,
          source_text: jdSourceMode.value === 'text' ? jdSourceText.value.trim() : undefined,
          department: department.value.trim(),
          category: jdCategory.value,
          target_position: targetPosition.value.trim() || undefined,
          target_position_source: jdTargetPositionSource.value,
          output_language: jdOutputLanguage()
        })
      : await submitProcessTask({
          file_id: uploadedFile.value!.file_id,
          original_filename: uploadedFile.value!.original_filename,
          template_id: selectedTemplate.value || undefined,
          language,
          jd_text: jdText.value || undefined,
          target_position: targetPosition.value.trim() || undefined,
          template_language: language,
          department: department.value.trim()
        })

    currentTaskId.value = res.data.task_id
    taskStatus.value = 'pending'
    taskProgress.value = 0
    taskSteps.value = []
    taskMessage.value = ''
    startPolling()
    return res.data.task_id
  }

  function startPolling() {
    stopPolling()
    isPolling.value = true
    pollTimer = setInterval(async () => {
      if (!currentTaskId.value) return stopPolling()
      try {
        const res = processingMode.value === 'jd'
          ? await getJDConversion(currentTaskId.value)
          : await getTaskStatus(currentTaskId.value)
        taskStatus.value = res.data.status
        taskProgress.value = res.data.progress
        taskMessage.value = processingMode.value === 'cv' && 'message' in res.data
          ? String(res.data.message || '')
          : ''
        taskSteps.value = (res.data.steps || []) as ProcessingStep[]
        taskError.value = res.data.error_message || ('error' in res.data ? res.data.error : null) || null

        if (res.data.status === 'awaiting_input') {
          requiredInput.value = res.data.required_input || { field: 'location', reason: 'missing_source_location' }
          stopPolling()
        } else if (res.data.status === 'completed') {
          requiredInput.value = null
          taskResult.value = res.data.result
          if (res.data.result) {
            if (processingMode.value === 'jd') {
              jdData.value = res.data.result.jd_data || null
              detectedTargetPosition.value = res.data.result.target_position || ''
              targetPosition.value = res.data.result.target_position || targetPosition.value
              jdGenerationMode.value = res.data.result.generation_mode || ''
              previewData.value = { position: jdData.value?.title_cn || jdData.value?.title_en, language: languageLabel() }
            } else {
              previewData.value = {
                name: res.data.result.anonymized_name || res.data.result.name,
                position: res.data.result.technical_area || res.data.result.resume_data?.technical_area || '',
                experience: res.data.result.total_exp,
                company: res.data.result.current_company,
                language: outputLanguage.value === 'en' ? 'English' : i18n.global.t('upload.chinese'),
                matchRate: res.data.result.match_rate,
                matchLevel: res.data.result.match_level,
                skills: res.data.result.skills
              }
              resumeData.value = res.data.result.resume_data || null
            }
          }
          stopPolling()
        } else if (res.data.status === 'failed') stopPolling()
      } catch {
        // Keep polling transient network failures.
      }
    }, 2000)
  }

  function languageLabel() {
    return outputLanguage.value === 'cnen' ? 'CN+EN' : outputLanguage.value === 'en' ? 'English' : i18n.global.t('upload.chinese')
  }

  async function regenerateJD(content: JDContent) {
    if (!currentTaskId.value) throw new Error('Missing JD task')
    taskStatus.value = 'processing'
    const res = await regenerateJDConversion(currentTaskId.value, content)
    taskStatus.value = res.data.status
    taskProgress.value = res.data.progress
    taskSteps.value = res.data.steps || []
    if (res.data.status === 'awaiting_input') {
      requiredInput.value = res.data.required_input || { field: 'location', reason: 'missing_source_location' }
      return jdData.value
    }
    requiredInput.value = null
    taskResult.value = res.data.result
    jdData.value = res.data.result?.jd_data || null
    return jdData.value
  }

  async function provideGender(gender: 'male' | 'female') {
    if (!currentTaskId.value) throw new Error('Missing CV task')
    await provideCVGender(currentTaskId.value, gender)
    requiredInput.value = null
    taskStatus.value = 'pending'
    startPolling()
  }

  async function provideJDLocation(location: string) {
    if (!currentTaskId.value) throw new Error('Missing JD task')
    taskStatus.value = 'processing'
    const res = await provideJDConversionLocation(currentTaskId.value, location.trim())
    taskStatus.value = res.data.status
    taskProgress.value = res.data.progress
    taskSteps.value = res.data.steps || []
    requiredInput.value = res.data.required_input || null
    taskResult.value = res.data.result
    if (res.data.result) {
      jdData.value = res.data.result.jd_data || null
      detectedTargetPosition.value = res.data.result.target_position || ''
      targetPosition.value = res.data.result.target_position || targetPosition.value
      jdGenerationMode.value = res.data.result.generation_mode || ''
      previewData.value = { position: jdData.value?.title_cn || jdData.value?.title_en, language: languageLabel() }
    }
    return res.data
  }

  async function refreshJDTask() {
    if (!currentTaskId.value) throw new Error('Missing JD task')
    const res = await getJDConversion(currentTaskId.value)
    const task = res.data
    taskStatus.value = task.status
    taskProgress.value = task.progress
    taskSteps.value = task.steps || []
    taskError.value = task.error_message || null

    if (task.status === 'awaiting_input') {
      requiredInput.value = task.required_input || { field: 'location', reason: 'missing_source_location' }
      stopPolling()
    } else if (task.status === 'completed') {
      requiredInput.value = null
      taskResult.value = task.result
      if (task.result) {
        jdData.value = task.result.jd_data || null
        detectedTargetPosition.value = task.result.target_position || ''
        targetPosition.value = task.result.target_position || targetPosition.value
        jdGenerationMode.value = task.result.generation_mode || ''
        previewData.value = { position: jdData.value?.title_cn || jdData.value?.title_en, language: languageLabel() }
      }
      stopPolling()
    } else if (task.status === 'failed') {
      requiredInput.value = null
      stopPolling()
    }
    return task
  }

  async function saveJDToLibrary() {
    if (!currentTaskId.value) throw new Error('Missing JD task')
    return saveJDConversion(currentTaskId.value)
  }

  function stopPolling() {
    isPolling.value = false
    if (pollTimer) clearInterval(pollTimer)
    pollTimer = null
  }

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
    taskMessage.value = ''
    requiredInput.value = null
    previewData.value = null
    resumeData.value = null
    jdData.value = null
    selectedTemplate.value = 'portrait'
    outputLanguage.value = 'zh'
    jdText.value = ''
    jdId.value = ''
    jdSourceMode.value = 'file'
    jdSourceText.value = ''
    jdCategory.value = 'technical'
    department.value = ''
    jdTargetPositionSource.value = 'content'
    detectedTargetPosition.value = ''
    isDetectingTargetPosition.value = false
    targetPositionDetectionError.value = null
    targetPositionRecognitionRequestId += 1
    jdGenerationMode.value = ''
    targetPosition.value = ''
    processingMode.value = 'cv'
  }

  return {
    uploadedFile, uploadProgress, isUploading, selectedTemplate, outputLanguage, jdText, jdId,
    jdSourceMode, jdSourceText, jdCategory, department, jdTargetPositionSource, detectedTargetPosition,
    isDetectingTargetPosition, targetPositionDetectionError,
    jdGenerationMode, targetPosition, processingMode, currentTaskId, taskStatus, taskProgress, taskSteps,
    taskResult, taskError, taskMessage, requiredInput, isPolling, previewData, resumeData, jdData,
    isProcessing, isAwaitingInput, isCompleted, isFailed, isIdle, uploadFile, submitTask, startPolling, stopPolling,
    recognizeTargetPosition, resetTargetPositionRecognition, regenerateJD, provideJDLocation, provideGender, refreshJDTask,
    saveJDToLibrary, resetAll, getTargetPositionLanguageMismatch
  }
})
