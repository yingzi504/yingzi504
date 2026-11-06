<template>
  <div class="upload-page">
    <div class="upload-layout">
      <!-- 左侧配置面板 -->
      <div class="config-panel" :class="{ 'is-cv': store.processingMode === 'cv' }">
        <!-- 模式切换标签（原型：位于左侧白框内顶部） -->
        <div class="mode-tabs">
          <button
            :class="['mode-tab', { active: store.processingMode === 'cv' }]"
            :disabled="!canUse('cv')"
            @click="switchProcessingMode('cv')"
          >
            {{ $t('upload.modeCV') }}
          </button>
          <button
            :class="['mode-tab', { active: store.processingMode === 'jd' }]"
            :disabled="!canUse('jd')"
            @click="switchProcessingMode('jd')"
          >
            {{ $t('upload.modeJD') }}
          </button>
        </div>

        <div v-if="store.processingMode === 'jd'" class="config-section jd-source-section">
          <label class="config-label">{{ $t('upload.jdSource') }}</label>
          <div class="toggle-group">
            <button :class="['toggle-btn', { active: store.jdSourceMode === 'file' }]" @click="setJDSourceMode('file')">
              {{ $t('upload.fileInput') }}
            </button>
            <button :class="['toggle-btn', { active: store.jdSourceMode === 'text' }]" @click="setJDSourceMode('text')">
              {{ $t('upload.jdTextInput') }}
            </button>
          </div>
        </div>

        <!-- 文件上传 -->
        <FileUpload
          v-if="store.processingMode === 'cv' || store.jdSourceMode === 'file'"
          :is-uploading="store.isUploading"
          @select="handleFileSelect"
          @remove="handleFileRemove"
        />

        <div
          v-else-if="store.processingMode === 'jd' && store.jdSourceMode === 'text'"
          class="jd-source-textarea"
        >
          <el-input
            v-model="store.jdSourceText"
            type="textarea"
            :rows="4"
            :placeholder="$t('upload.jdSourcePlaceholder')"
            resize="none"
          />
        </div>

        <!-- PPT模板选择（仅CV模式） -->
        <div v-if="store.processingMode === 'cv'" class="config-section template-section">
          <label class="config-label">{{ $t('upload.pptTemplate') }}</label>
          <div class="toggle-group">
            <button
              v-for="t in templateOptions"
              :key="t.value"
              :class="['toggle-btn', { active: store.selectedTemplate === t.value }]"
              @click="store.selectedTemplate = t.value"
            >
              {{ t.label }}
            </button>
          </div>
        </div>

        <!-- 输出语言 -->
        <div class="config-section language-section">
          <label class="config-label">{{ $t('upload.outputLang') }}</label>
          <div class="toggle-group">
            <button
              :class="['toggle-btn', { active: store.outputLanguage === 'zh' }]"
              @click="store.outputLanguage = 'zh'"
            >
              {{ $t('upload.chinese') }}
            </button>
            <button
              :class="['toggle-btn', { active: store.outputLanguage === 'en' }]"
              @click="store.outputLanguage = 'en'"
            >
              {{ $t('upload.english') }}
            </button>
            <!-- JD 模式额外选项 -->
            <button
              v-if="store.processingMode === 'jd'"
              :class="['toggle-btn', { active: store.outputLanguage === 'cnen' }]"
              @click="store.outputLanguage = 'cnen'"
            >
              {{ $t('upload.cnEn') }}
            </button>
          </div>
        </div>

        <!-- CV/JD 共用固定部门目录；CV 必填并用于完成后的自动归档。 -->
        <div v-if="store.processingMode === 'cv'" class="config-section">
          <label class="config-label">
            {{ $t('upload.department') }}
            <span class="required-tag">{{ $t('upload.required') }}</span>
          </label>
          <el-select
            v-model="store.department"
            :placeholder="$t('upload.deptSelectPlaceholder')"
            filterable
            style="width: 100%"
          >
            <el-option v-for="code in departmentCodes" :key="code" :label="code" :value="code" />
          </el-select>
        </div>

        <div v-if="store.processingMode === 'cv'" class="config-section target-position-section">
          <label class="config-label">
            {{ $t('upload.targetJob') }}
            <span class="optional-tag">{{ $t('upload.optional') }}</span>
          </label>
          <el-input
            v-model="store.targetPosition"
            clearable
            :placeholder="$t('upload.targetJobPlaceholder')"
          />
          <p v-if="store.getTargetPositionLanguageMismatch()" class="target-position-error">
            {{ $t('upload.targetPositionLanguageMismatch') }}
          </p>
        </div>

        <div v-if="store.processingMode === 'jd'" class="config-section">
          <label class="config-label">{{ $t('upload.department') }}</label>
          <el-select
            v-model="store.department"
            :placeholder="$t('upload.deptPlaceholder')"
            clearable
            style="width: 100%"
          >
            <el-option v-for="code in departmentCodes" :key="code" :label="code" :value="code" />
          </el-select>
        </div>

        <div v-if="store.processingMode === 'jd'" class="config-section">
          <label class="config-label">{{ $t('upload.jobCategory') }}</label>
          <div class="toggle-group">
            <button :class="['toggle-btn', { active: store.jdCategory === 'technical' }]" @click="store.jdCategory = 'technical'">{{ $t('upload.technical') }}</button>
            <button :class="['toggle-btn', { active: store.jdCategory === 'non_technical' }]" @click="store.jdCategory = 'non_technical'">{{ $t('upload.nonTechnical') }}</button>
          </div>
        </div>

        <div v-if="store.processingMode === 'jd'" class="config-section">
          <label class="config-label">{{ $t('upload.jdLabelTarget') }}</label>
          <div class="toggle-group target-source-toggle">
            <button :class="['toggle-btn', { active: store.jdTargetPositionSource === 'manual' }]" @click="handleJDTargetPositionSource('manual')">{{ $t('upload.positionManual') }}</button>
            <button :class="['toggle-btn', { active: store.jdTargetPositionSource === 'filename' }]" :disabled="store.jdSourceMode !== 'file'" @click="handleJDTargetPositionSource('filename')">{{ $t('upload.positionFilename') }}</button>
            <button :class="['toggle-btn', { active: store.jdTargetPositionSource === 'content' }]" @click="handleJDTargetPositionSource('content')">{{ $t('upload.positionContent') }}</button>
          </div>
          <el-input
            v-model="store.targetPosition"
            class="target-position-input"
            clearable
            :disabled="store.isDetectingTargetPosition"
            :placeholder="jdTargetPositionPlaceholder"
            @input="store.targetPositionDetectionError = null"
          >
            <template v-if="store.isDetectingTargetPosition" #suffix>
              <el-icon class="target-position-loading"><Loading /></el-icon>
            </template>
          </el-input>
        </div>

        <!-- 岗位描述 / 目标岗位方向 -->
        <div v-if="store.processingMode === 'cv'" class="config-section">
          <label class="config-label">
            {{ store.processingMode === 'cv' ? $t('upload.jdLabel') : $t('upload.jdLabelTarget') }}
            <span class="optional-tag">{{ $t('upload.optional') }}</span>
          </label>

          <!-- JD 输入方式切换（仅 CV 模式） -->
          <div v-if="store.processingMode === 'cv'" class="toggle-group jd-mode-toggle">
            <button
              :class="['toggle-btn', { active: jdInputMode === 'library' }]"
              :disabled="!canUse('library')"
              @click="jdInputMode = 'library'"
            >
              {{ $t('upload.jdFromLibrary') }}
            </button>
            <button
              :class="['toggle-btn', { active: jdInputMode === 'text' }]"
              @click="jdInputMode = 'text'"
            >
              {{ $t('upload.jdTextInput') }}
            </button>
          </div>

          <!-- JD 库搜索选择 -->
          <div v-if="store.processingMode === 'cv' && jdInputMode === 'library'" class="jd-select-wrapper">
            <el-select
              v-model="selectedJdId"
              filterable
              remote
              reserve-keyword
              clearable
              :remote-method="searchJDs"
              :loading="jdSearchLoading"
              :placeholder="$t('upload.jdSearchPlaceholder')"
              popper-class="jd-select-popper"
              @change="onJdSelected"
              style="width: 100%"
            >
              <el-option
                v-for="jd in jdOptions"
                :key="jd.id"
                :label="jd.position"
                :value="jd.id"
              >
                <div class="jd-option">
                  <span class="jd-option-title">{{ jd.position }}</span>
                  <span v-if="jd.department" class="jd-option-dept">{{ jd.department }}</span>
                  <span v-if="jd.usageCount" class="jd-option-count">{{ $t('upload.jdUsageCount', { count: jd.usageCount }) }}</span>
                </div>
              </el-option>
            </el-select>
            <!-- 选中JD内容预览 -->
            <div v-if="selectedJdContent" class="jd-preview">
              {{ selectedJdContent.slice(0, 120) }}{{ selectedJdContent.length > 120 ? '...' : '' }}
            </div>
          </div>

          <!-- 文本输入（CV模式的备选 或 JD模式） -->
          <div v-if="store.processingMode !== 'cv' || jdInputMode === 'text'" class="jd-textarea-wrapper">
            <el-input
              v-model="store.jdText"
              type="textarea"
              :rows="3"
              :placeholder="store.processingMode === 'cv' ? $t('upload.jdTextPlaceholder') : $t('upload.jdTargetPlaceholder')"
              resize="none"
            />
          </div>
        </div>

        <!-- 开始处理按钮 -->
        <el-button
          type="primary"
          size="large"
          class="submit-btn"
          :loading="store.isProcessing"
          :disabled="!canSubmit"
          @click="handleSubmit"
        >
          {{ store.isProcessing ? $t('upload.processing') : $t('upload.startProcess') }}
        </el-button>
      </div>

      <!-- 右侧结果面板：左信息+按钮 / 右预览区，匹配原型图 -->
      <div class="result-panel">
        <!-- 左栏：人员信息 + 操作按钮 -->
        <div v-if="hasCompletedResult" class="result-left">
          <!-- 标题随模式切换 -->
          <h3 class="panel-title">{{ store.processingMode === 'cv' ? $t('upload.cvInfo') : $t('upload.jdInfo') }}</h3>

          <!-- CV 模式：匹配度常显 -->
          <div v-if="store.processingMode === 'cv'" class="match-section">
            <div class="match-card">
              <div class="match-score">{{ store.previewData?.matchRate || '—' }}</div>
              <div class="match-info">
                <p class="match-label">{{ $t('upload.matchRate') }}</p>
                <p class="match-level">{{ store.previewData?.matchLevel || $t('upload.noMatch') }}</p>
              </div>
            </div>
          </div>

          <!-- 信息字段（标签在上，值在下，两行展示） -->
          <div class="info-grid">
            <div class="info-item">
              <span class="info-key">
                {{ store.processingMode === 'jd' ? $t('upload.department') : $t('upload.anonymizedName') }}
              </span>
              <span class="info-value">{{ store.previewData?.name || '—' }}</span>
            </div>
            <div class="info-item">
              <span class="info-key">{{ $t('upload.targetPosition') }}</span>
              <span class="info-value">{{ store.previewData?.position || '—' }}</span>
            </div>
            <div v-if="store.processingMode === 'cv'" class="info-item">
              <span class="info-key">{{ $t('upload.workYears') }}</span>
              <span class="info-value">{{ store.previewData?.experience || '—' }}</span>
            </div>
            <div v-if="store.processingMode === 'cv'" class="info-item">
              <span class="info-key">{{ $t('upload.currentCompany') }}</span>
              <span class="info-value">{{ store.previewData?.company || '—' }}</span>
            </div>
            <div class="info-item">
              <span class="info-key">{{ $t('upload.language') }}</span>
              <span class="info-value">{{ store.previewData?.language || '—' }}</span>
            </div>
          </div>

          <!-- 操作按钮（左下方，始终显示） -->
          <div v-if="hasCompletedResult" class="action-buttons">
            <!-- 下载按钮 — CV:下载PPT+下载PDF / JD:下载WORD+下载PDF，纵列排放 -->
            <div class="download-group">
              <el-button
                type="primary"
                size="small"
                :disabled="!store.isCompleted && !store.previewData"
                @click="handleDownload(store.processingMode === 'cv' ? 'pptx' : 'docx')"
              >
                {{ store.processingMode === 'cv' ? $t('upload.downloadPPT') : $t('upload.downloadWord') }}
              </el-button>
              <el-button
                type="primary"
                size="small"
                :disabled="!store.isCompleted && !store.previewData"
                @click="handleDownload('pdf')"
              >
                {{ $t('upload.downloadPDF') }}
              </el-button>
            </div>
            <el-button
              class="btn-edit"
              size="small"
              :disabled="!store.isCompleted && !store.previewData"
              @click="handleEdit"
            >
              {{ $t('upload.editContent') }}
            </el-button>
            <el-button
              v-if="store.processingMode === 'jd'"
              class="btn-save"
              size="small"
              :disabled="!store.isCompleted && !store.previewData"
              @click="handleSaveToJD"
            >
              {{ $t('upload.saveToJD') }}
            </el-button>
            <el-button
              class="btn-retry"
              size="small"
              :disabled="!store.isCompleted && !store.previewData"
              @click="handleRetry"
            >
              {{ $t('upload.retry') }}
            </el-button>
          </div>
        </div>

        <!-- 右栏：预览区（撑满右侧） -->
        <div class="result-right">
          <div class="preview-area">
            <!-- 已完成：展示简历内容预览 -->
            <div
              v-if="hasCompletedResult && store.processingMode === 'jd' && store.jdData"
              class="resume-preview-content jd-preview-content"
            >
              <div class="preview-header">
                <h3 class="preview-name">{{ displayJDTitle }}</h3>
                <p v-if="store.jdData.department" class="preview-position">{{ store.jdData.department }}</p>
                <p v-if="displayJDLocation" class="preview-meta">{{ displayJDLocation }}</p>
              </div>

              <div v-if="displayJDResponsibilities.length" class="preview-section">
                <h4 class="section-title">{{ $t('upload.responsibilities') }}</h4>
                <ul class="jd-list">
                  <li v-for="(item, index) in displayJDResponsibilities" :key="`responsibility-${index}`">
                    {{ item }}
                  </li>
                </ul>
              </div>

              <div
                v-for="group in jdRequirementGroups"
                :key="group.key"
                v-show="group.items.length"
                class="preview-section"
              >
                <h4 class="section-title">{{ group.label }}</h4>
                <ul class="jd-list">
                  <li v-for="(item, index) in group.items" :key="`${group.key}-${index}`">{{ item }}</li>
                </ul>
              </div>
            </div>

            <div v-else-if="hasCompletedResult && store.processingMode === 'cv'" class="resume-preview-content">
              <!-- 头部：姓名 + 职位 -->
              <div class="preview-header">
                <h3 class="preview-name">{{ store.previewData?.name || '—' }}</h3>
                <p class="preview-position">{{ store.previewData?.position || $t('upload.noPosition') }}</p>
                <p class="preview-meta" v-if="store.previewData?.experience">
                  {{ $t('upload.yearsExperience', { exp: store.previewData.experience, company: store.previewData.company }) }}
                </p>
              </div>

              <!-- 个人简介 -->
              <div v-if="store.resumeData?.summary" class="preview-section">
                <h4 class="section-title">{{ $t('upload.summary') }}</h4>
                <p class="preview-summary">{{ store.resumeData.summary }}</p>
              </div>

              <!-- 工作经历 -->
              <div v-if="store.resumeData?.work?.length" class="preview-section">
                <h4 class="section-title">{{ $t('upload.workExperience') }}</h4>
                <div v-for="(w, i) in store.resumeData.work" :key="'w'+i" class="preview-item">
                  <div class="item-header">
                    <span class="item-company">{{ w.company }}</span>
                    <span class="item-period">{{ w.period }}</span>
                  </div>
                  <p class="item-role" v-if="w.role">{{ w.role }}</p>
                  <p class="item-tasks" v-if="w.tasks">{{ w.tasks }}</p>
                </div>
              </div>

              <!-- 项目经历 -->
              <div v-if="store.resumeData?.project?.length" class="preview-section">
                <h4 class="section-title">{{ $t('upload.projectExperience') }}</h4>
                <div v-for="(p, i) in store.resumeData.project" :key="'p'+i" class="preview-item">
                  <div class="item-header">
                    <span class="item-company">{{ p.name || p.company }}</span>
                    <span class="item-period">{{ p.period }}</span>
                  </div>
                  <p class="item-role" v-if="p.role">{{ p.role }}</p>
                  <p class="item-tasks" v-if="p.tasks">{{ p.tasks }}</p>
                </div>
              </div>

              <!-- 教育经历 -->
              <div v-if="store.resumeData?.education?.length" class="preview-section">
                <h4 class="section-title">{{ $t('upload.education') }}</h4>
                <div v-for="(e, i) in store.resumeData.education" :key="'e'+i" class="preview-item">
                  <div class="item-header">
                    <span class="item-company">{{ e.school }}</span>
                    <span class="item-period">{{ e.period }}</span>
                  </div>
                  <p class="item-role" v-if="e.degree || e.major">{{ [e.degree, e.major].filter(Boolean).join(' · ') }}</p>
                </div>
              </div>

              <!-- 技能 -->
              <div v-if="store.resumeData?.tech_skills || store.resumeData?.lang_skills" class="preview-section">
                <h4 class="section-title">{{ $t('upload.skills') }}</h4>
                <div class="preview-skills">
                  <span v-if="store.resumeData.tech_skills" class="skill-tag">{{ store.resumeData.tech_skills }}</span>
                  <span v-if="store.resumeData.lang_skills" class="skill-tag">{{ store.resumeData.lang_skills }}</span>
                </div>
              </div>
            </div>

            <!-- 空状态 -->
            <div v-else-if="store.isProcessing" class="empty-preview is-processing">
              <el-icon :size="36" class="empty-preview-icon is-loading"><Loading /></el-icon>
              <p class="empty-preview-title">{{ $t('upload.processing') }}</p>
              <p>{{ $t('upload.previewProcessingHint') }}</p>
            </div>

            <div v-else-if="store.isAwaitingInput" class="empty-preview is-awaiting">
              <el-icon :size="36" class="empty-preview-icon"><LocationInformation /></el-icon>
              <p class="empty-preview-title">{{ store.requiredInput?.field === 'gender' ? $t('upload.genderTitle') : $t('upload.previewAwaitingTitle') }}</p>
              <p>{{ store.requiredInput?.field === 'gender' ? $t('upload.genderDescription') : $t('upload.previewAwaitingHint') }}</p>
            </div>

            <div v-else-if="store.isFailed" class="empty-preview is-failed">
              <el-icon :size="36" class="empty-preview-icon"><CircleCloseFilled /></el-icon>
              <p class="empty-preview-title">{{ $t('upload.previewFailedTitle') }}</p>
              <p class="empty-preview-detail">{{ store.taskError || $t('upload.previewFailedHint') }}</p>
            </div>

            <div v-else class="empty-preview is-idle">
              <el-icon :size="36" class="empty-preview-icon"><Document /></el-icon>
              <p>{{ store.processingMode === 'jd' ? $t('upload.emptyJDTitle1') : $t('upload.emptyTitle1') }}</p>
              <p>{{ store.processingMode === 'jd' ? $t('upload.emptyJDTitle2') : $t('upload.emptyTitle2') }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 底部进度条（始终显示，hover 查看步骤） -->
    <el-dialog
      v-model="locationDialogVisible"
      :title="$t('upload.locationDialogTitle')"
      width="420px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
      class="location-dialog"
    >
      <p class="location-dialog-description">{{ $t('upload.locationDialogDescription') }}</p>
      <el-input
        v-model="locationInput"
        :placeholder="$t('upload.locationPlaceholder')"
        autofocus
        @keyup.enter="handleLocationSubmit"
      />
      <template #footer>
        <el-button
          type="primary"
          :loading="locationSubmitting"
          :disabled="locationSubmitting || !locationInput.trim()"
          @click="handleLocationSubmit"
        >
          {{ $t('upload.confirmLocation') }}
        </el-button>
      </template>
    </el-dialog>

    <el-dialog
      :model-value="store.processingMode === 'cv' && store.requiredInput?.field === 'gender'"
      :title="$t('upload.genderTitle')"
      width="min(420px, 92vw)"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <p style="margin-bottom: 16px">{{ $t('upload.genderDescription') }}</p>
      <el-radio-group v-model="genderInput" :disabled="genderSubmitting" :aria-label="$t('upload.genderTitle')">
        <el-radio value="male">{{ $t('upload.genderMale') }}</el-radio>
        <el-radio value="female">{{ $t('upload.genderFemale') }}</el-radio>
      </el-radio-group>
      <template #footer>
        <el-button type="primary" :loading="genderSubmitting" :disabled="!genderInput || genderSubmitting" @click="handleGenderSubmit">
          {{ $t('upload.genderContinue') }}
        </el-button>
      </template>
    </el-dialog>

    <div class="bottom-bar">
      <ProgressBar
        :label="progressLabel"
        :percent="store.taskProgress"
        :status="store.taskStatus"
        :steps="store.taskSteps"
      />
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { CircleCloseFilled, Document, Loading, LocationInformation } from '@element-plus/icons-vue'
import { useProcessingStore } from '@/stores/processing-advanced'
import { downloadOutput } from '@/api/resume'
import { canUse } from '@/stores/auth'
import { downloadJDConversion, saveJDConversion } from '@/api/jd-conversion'
import { getJDs } from '@/api/jd'
import type { JDItem } from '@/types'
import FileUpload from '@/components/FileUpload.vue'
import ProgressBar from '@/components/ProgressBar.vue'
import { DEPARTMENT_CODES } from '@/utils/departments'

const { t } = useI18n()
const store = useProcessingStore()
if (!canUse(store.processingMode || 'cv')) store.processingMode = canUse('cv') ? 'cv' : 'jd'
const genderInput = ref<'' | 'male' | 'female'>('')
const genderSubmitting = ref(false)
watch(() => store.currentTaskId, () => { genderInput.value = '' })
async function handleGenderSubmit() {
  if (!genderInput.value || genderSubmitting.value) return
  genderSubmitting.value = true
  try {
    await store.provideGender(genderInput.value)
  } catch {
    ElMessage.error(t('upload.genderSubmitFailed'))
  } finally {
    genderSubmitting.value = false
  }
}
const locationInput = ref('')
const locationDialogVisible = ref(false)
const locationSubmitting = ref(false)
const departmentCodes = DEPARTMENT_CODES

watch(
  () => [store.isAwaitingInput, store.requiredInput?.field, store.processingMode, store.isProcessing] as const,
  ([awaitingInput, requiredField, processingMode, processing]) => {
    const needsLocation = processingMode === 'jd' && (awaitingInput || requiredField === 'location')
    if (needsLocation) {
      locationDialogVisible.value = true
    } else if (!processing) {
      locationDialogVisible.value = false
      locationInput.value = ''
    }
  },
  { immediate: true }
)

const templateOptions = computed(() => [
  { value: 'portrait', label: t('upload.portrait') },
  { value: 'landscape', label: t('upload.landscape') }
])

const displayJDTitle = computed(() => {
  const content = store.jdData
  if (!content) return ''
  if (store.outputLanguage === 'zh') return content.title_cn || content.title_en
  if (store.outputLanguage === 'en') return content.title_en || content.title_cn
  return [content.title_cn, content.title_en].filter(Boolean).join(' / ')
})

const displayJDLocation = computed(() => {
  const content = store.jdData
  if (!content) return ''
  if (store.outputLanguage === 'zh') return content.location_cn || content.location_en
  if (store.outputLanguage === 'en') return content.location_en || content.location_cn
  return [content.location_cn, content.location_en].filter(Boolean).join(' / ')
})

const displayJDResponsibilities = computed(() => {
  const content = store.jdData
  if (!content) return []
  return selectBilingualItems(content.responsibilities_cn, content.responsibilities_en)
})

const jdRequirementGroups = computed(() => {
  const requirements = store.jdData?.requirements
  if (!requirements) return []
  return [
    { key: 'education', label: t('upload.requirementEducation'), items: selectBilingualItems(requirements.education.cn, requirements.education.en) },
    { key: 'experience', label: t('upload.requirementExperience'), items: selectBilingualItems(requirements.experience.cn, requirements.experience.en) },
    { key: 'required_skills', label: t('upload.requirementSkills'), items: selectBilingualItems(requirements.required_skills.cn, requirements.required_skills.en) },
    { key: 'language', label: t('upload.requirementLanguage'), items: selectBilingualItems(requirements.language.cn, requirements.language.en) },
    { key: 'preferred', label: t('upload.requirementPreferred'), items: selectBilingualItems(requirements.preferred.cn, requirements.preferred.en) },
    { key: 'soft_skills', label: t('upload.requirementSoftSkills'), items: selectBilingualItems(requirements.soft_skills.cn, requirements.soft_skills.en) }
  ]
})

const hasCompletedResult = computed(() => {
  if (!store.isCompleted) return false
  return store.processingMode === 'jd'
    ? !!store.jdData
    : !!(store.previewData || store.resumeData)
})

function selectBilingualItems(cn: string[], en: string[]): string[] {
  if (store.outputLanguage === 'zh') return cn
  if (store.outputLanguage === 'en') return en
  const length = Math.max(cn.length, en.length)
  return Array.from({ length }, (_, index) => [cn[index], en[index]].filter(Boolean).join(' / '))
}

// JD 双选模式
// JD input mode
const jdInputMode = ref<'library' | 'text'>('text')
const jdSearchLoading = ref(false)
const jdOptions = ref<JDItem[]>([])
const selectedJdId = ref('')
const selectedJdContent = ref('')

const canSubmit = computed(() => {
  if (!store.outputLanguage || store.isAwaitingInput || store.isProcessing || store.isDetectingTargetPosition) return false
  if (store.processingMode === 'cv') {
    if (store.outputLanguage === 'cnen') return false
    if (store.getTargetPositionLanguageMismatch()) return false
    return !!store.uploadedFile && !!store.selectedTemplate
  }
  const sourceReady = store.jdSourceMode === 'file' ? !!store.uploadedFile : !!store.jdSourceText.trim()
  if (!sourceReady) return false
  return !!store.targetPosition.trim()
})

const jdTargetPositionPlaceholder = computed(() => {
  if (store.isDetectingTargetPosition) return t('upload.positionRecognizing')
  if (store.targetPositionDetectionError) return t('upload.positionRecognitionFailed')
  return store.jdTargetPositionSource === 'manual'
    ? t('upload.targetJobPlaceholder')
    : t('upload.positionAutoPlaceholder')
})

function switchProcessingMode(mode: 'cv' | 'jd') {
  if (!canUse(mode)) return
  if (store.isProcessing || store.isAwaitingInput) return
  if (store.processingMode !== mode) {
    store.resetTargetPositionRecognition()
  }
  store.processingMode = mode
  if (mode === 'cv' && store.outputLanguage === 'cnen') {
    store.outputLanguage = 'zh'
  }
}

const lastTargetPositionMismatch = ref('')
watch(
  () => [store.processingMode, store.targetPosition, store.outputLanguage] as const,
  () => {
    const mismatch = store.processingMode === 'cv'
      ? store.getTargetPositionLanguageMismatch()
      : null
    if (!mismatch) {
      lastTargetPositionMismatch.value = ''
      return
    }
    const key = `${mismatch.positionLanguage}:${mismatch.outputLanguage}`
    if (key !== lastTargetPositionMismatch.value) {
      lastTargetPositionMismatch.value = key
      ElMessage.warning(t('upload.targetPositionLanguageMismatch'))
    }
  }
)

watch(
  () => store.jdSourceText,
  () => {
    if (
      store.processingMode === 'jd'
      && store.jdSourceMode === 'text'
      && store.jdTargetPositionSource === 'content'
      && store.detectedTargetPosition
    ) {
      store.resetTargetPositionRecognition()
    }
  }
)

watch(
  () => store.outputLanguage,
  () => {
    if (
      store.processingMode === 'jd'
      && store.jdTargetPositionSource !== 'manual'
      && (store.isDetectingTargetPosition || store.detectedTargetPosition)
    ) {
      store.resetTargetPositionRecognition()
    }
  }
)

function setJDSourceMode(mode: 'file' | 'text') {
  store.resetTargetPositionRecognition()
  store.jdSourceMode = mode
  if (mode === 'text') store.uploadedFile = null
  if (mode === 'text' && store.jdTargetPositionSource === 'filename') {
    store.jdTargetPositionSource = 'content'
  }
}

async function handleJDTargetPositionSource(source: 'manual' | 'filename' | 'content') {
  if (source === 'manual') {
    store.resetTargetPositionRecognition()
    store.jdTargetPositionSource = source
    return
  }
  if (store.isDetectingTargetPosition) return
  store.jdTargetPositionSource = source
  try {
    await store.recognizeTargetPosition(source)
  } catch {
    ElMessage.error(t('upload.positionRecognitionFailed'))
  }
}

async function searchJDs(keyword: string) {
  if (!keyword || keyword.length < 1) {
    jdOptions.value = []
    return
  }
  jdSearchLoading.value = true
  try {
    const res = await getJDs({ keyword, pageSize: 20 })
    jdOptions.value = res.data?.items || res.data || []
  } catch {
    jdOptions.value = []
  } finally {
    jdSearchLoading.value = false
  }
}

function onJdSelected(id: string) {
  if (!id) {
    selectedJdContent.value = ''
    store.jdText = ''
    store.jdId = ''
    return
  }
  const jd = jdOptions.value.find(item => item.id === id)
  if (jd) {
    selectedJdContent.value = jd.content || ''
    store.jdText = jd.content || ''
    store.jdId = jd.id
  }
}

const progressLabel = computed(() => {
  const mode = store.processingMode === 'cv' ? 'CV' : 'JD'
  if (store.isFailed) return t('upload.failedLabel', { mode })
  if (store.taskStatus === 'processing' && store.taskMessage) return store.taskMessage
  return t('upload.progressLabel', { mode })
})

async function handleFileSelect(file: File) {
  store.resetTargetPositionRecognition()
  try {
    await store.uploadFile(file)
    ElMessage.success(t('upload.uploadSuccess'))
  } catch {
    ElMessage.error(t('upload.uploadFailed'))
  }
}

function handleFileRemove() {
  store.resetTargetPositionRecognition()
  store.uploadedFile = null
  store.uploadProgress = 0
}

async function handleSubmit() {
  if (store.processingMode === 'cv' && !store.department) {
    ElMessage.warning(t('upload.pleaseFillDepartment'))
    return
  }
  if (store.processingMode === 'cv' && store.getTargetPositionLanguageMismatch()) {
    ElMessage.warning(t('upload.targetPositionLanguageMismatch'))
    return
  }
  try {
    await store.submitTask()
  } catch (error) {
    const message = error instanceof Error ? error.message : ''
    if (message === t('upload.targetPositionLanguageMismatch')) {
      ElMessage.warning(message)
    } else {
      ElMessage.error(t('upload.taskSubmitFailed'))
    }
  }
}

async function handleDownload(format: 'pptx' | 'pdf' | 'docx') {
  if (!store.currentTaskId) return
  try {
    const blob = store.processingMode === 'jd'
      ? await downloadJDConversion(store.currentTaskId, format === 'pdf' ? 'pdf' : 'docx')
      : await downloadOutput(store.currentTaskId, format)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    // 优先使用后端返回的 output_filename，确保文件名格式正确
    const outputFilename = store.taskResult?.output_filename
    if (outputFilename) {
      a.download = format === 'pptx' ? outputFilename : outputFilename.replace(/\.pptx$/i, `.${format}`)
    } else {
      a.download = `resume_output.${format}`
    }
    a.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error(t('upload.downloadFailed'))
  }
}

function handleEdit() {
  ElMessage.info(t('upload.editComingSoon'))
}

async function handleSaveToJD() {
  if (!store.currentTaskId) return
  try {
    await saveJDConversion(store.currentTaskId)
    ElMessage.success(t('upload.savedToJD'))
  } catch {
    ElMessage.error(t('upload.saveToJDFailed'))
  }
}

async function handleLocationSubmit() {
  const location = locationInput.value.trim()
  if (!location || locationSubmitting.value) return
  locationSubmitting.value = true
  try {
    await store.provideJDLocation(location)
    locationInput.value = ''
  } catch {
    // A second tab or an earlier click may have completed the task already.
    // Refresh it so a stale dialog does not keep submitting an old task.
    try {
      const task = await store.refreshJDTask()
      if (task.status === 'completed') locationInput.value = ''
    } catch {
      ElMessage.error(t('upload.locationSubmitFailed'))
    }
  } finally {
    locationSubmitting.value = false
  }
}

function handleRetry() {
  store.resetAll()
}
</script>

<style scoped>
.upload-page {
  display: flex;
  flex-direction: column;
  height: 100%;
  gap: 8px;
}

/* 模式切换 — 放在 config-panel 顶部，撑满宽度 */
.mode-tabs {
  display: flex;
  background: var(--app-primary-soft);
  border-radius: 20px;
  padding: 2px;
  width: 100%;
}

.mode-tab {
  flex: 1;
  padding: 5px 0;
  border: none;
  border-radius: 18px;
  font-size: 12px;
  cursor: pointer;
  color: var(--app-primary);
  background: transparent;
  transition: all 0.2s;
  text-align: center;
  white-space: nowrap;
}

.mode-tab.active {
  background: var(--app-primary);
  color: #fff;
  font-weight: 600;
}

/* 主布局 */
.upload-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.config-panel {
  width: 340px;
  flex-shrink: 0;
  background: #fff;
  border-radius: 10px;
  padding: 10px;
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  align-content: start;
  min-width: 0;
  min-height: 0;
  gap: 8px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  overflow-y: auto;
}

.result-panel {
  min-width: 0;
  flex: 1;
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  display: flex;
  gap: 16px;
  overflow: hidden;
}

/* 左栏：人员信息 + 按钮 */
.result-left {
  width: 170px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
  overflow-y: auto;
}

/* 右栏：预览区撑满 */
.result-right {
  flex: 1;
  display: flex;
  min-width: 0;
}

/* 配置区 */
.config-section {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.config-label {
  font-size: 11px;
  font-weight: 600;
  color: #5A5A7A;
}

.target-position-error {
  margin: 0;
  color: #D14343;
  font-size: 10px;
  line-height: 1.4;
}

.optional-tag {
  font-weight: 400;
  color: #9CA3C4;
  font-size: 10px;
}
.required-tag {
  margin-left: 6px;
  padding: 1px 5px;
  border-radius: 4px;
  background: #f1eafb;
  color: var(--app-primary-dark);
  font-size: 9px;
  font-weight: 600;
}

.toggle-group {
  display: flex;
  gap: 4px;
}

.toggle-btn {
  flex: 1;
  min-height: 27px;
  padding: 5px 0;
  border: none;
  border-radius: 6px;
  font-size: 10.5px;
  line-height: 1.2;
  cursor: pointer;
  background: #F5F6FA;
  color: #5A5A7A;
  transition: all 0.2s;
}

.toggle-btn.active {
  background: var(--app-primary);
  color: #fff;
  font-weight: 600;
}
/* 小号切换按钮（JD输入方式） */
.toggle-sm {
  padding: 5px 0;
  font-size: 10.5px;
  border-radius: 4px;
}

/* JD选择器包装 */
.jd-select-wrapper {
  display: flex;
  flex-direction: column;
  gap: 4px;
  margin-top: 4px;
}

/* JD文本输入包装 */
.jd-textarea-wrapper {
  margin-top: 4px;
}

/* Keep the JD source textarea aligned with the file upload control. */
.jd-source-textarea {
  width: 100%;
}

.target-position-loading {
  color: var(--app-primary);
  animation: rotating 1.4s linear infinite;
}

/* JD选项行 */
.jd-option {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
  overflow: hidden;
}

.jd-option-title {
  flex: 1;
  font-size: 12px;
  color: #333;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.jd-option-dept {
  font-size: 10px;
  color: #9CA3C4;
  flex-shrink: 0;
}

.jd-option-count {
  font-size: 10px;
  color: var(--app-primary);
  flex-shrink: 0;
}

/* JD预览文本 */
.jd-preview {
  font-size: 11px;
  color: #7B7B9A;
  background: var(--app-primary-surface);
  border: 1px solid var(--app-primary-soft);
  border-radius: 4px;
  padding: 6px 8px;
  line-height: 1.5;
  word-break: break-all;
}
.submit-btn {
  width: 100%;
  height: 32px;
  font-size: 12px;
  font-weight: 600;
  border-radius: 8px;
  margin-top: 0;
}

/* Keep the upload control compact enough for the complete configuration to fit in one viewport. */
.config-panel :deep(.file-upload) {
  min-height: 104px;
  padding: 8px;
}

.config-panel :deep(.upload-icon) {
  width: 24px;
  height: 24px;
  margin: 0 0 4px;
}

.config-panel :deep(.upload-icon .el-icon) {
  font-size: 24px;
}

.config-panel :deep(.upload-hint) {
  margin-bottom: 6px;
}

.config-panel :deep(.upload-or) {
  margin-top: 4px;
}

.config-panel :deep(.el-input__wrapper),
.config-panel :deep(.el-select__wrapper) {
  min-height: 28px;
  padding: 1px 8px;
  font-size: 12px;
}

.config-panel :deep(.el-textarea__inner) {
  padding: 5px 9px;
  line-height: 1.35;
  font-size: 12px;
}

/* 结果面板 */
@media (min-width: 761px) and (max-height: 820px) {
  .config-panel {
    padding: 10px;
    gap: 6px;
  }

  .config-section {
    gap: 3px;
  }

  .toggle-btn {
    min-height: 25px;
    padding: 4px 0;
  }

  .submit-btn {
    height: 30px;
  }

  .config-panel :deep(.file-upload) {
    min-height: 100px;
    padding: 8px;
  }

  .config-panel :deep(.upload-icon) {
    width: 28px;
    height: 28px;
    margin-bottom: 2px;
  }

  .config-panel :deep(.upload-icon .el-icon) {
    font-size: 21px;
  }

  .config-panel :deep(.upload-hint) {
    margin-bottom: 4px;
  }
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #1E1E2D;
}

.match-section {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}

.match-card {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--app-primary-soft);
  border-radius: 8px;
  padding: 10px 14px;
  flex-shrink: 0;
}

.match-score {
  width: 38px;
  height: 38px;
  background: var(--app-primary);
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.match-label {
  font-size: 11px;
  font-weight: 600;
  color: var(--app-primary);
}

.match-level {
  font-size: 10px;
  color: #5A5A7A;
}

.match-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
  padding-top: 4px;
}

.tag {
  font-size: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.tag-success {
  background: #ECFDF5;
  color: #22C55E;
}

.tag-warning {
  background: #FFFBEB;
  color: #F59E0B;
}

/* 信息网格 — 标签在上、值在下，两行展示 */
.info-grid {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.info-key {
  font-size: 10px;
  color: #9CA3C4;
}

.info-value {
  font-size: 12px;
  font-weight: 600;
  color: #1E1E2D;
}

/* 预览区 */
.preview-area {
  flex: 1;
  border: 2px solid var(--app-primary);
  border-radius: 8px;
  background: var(--app-primary-surface);
  min-height: 0;
  overflow: hidden;
}

/* 空状态（居中展示） */
.preview-area:has(.empty-preview) {
  display: flex;
  align-items: center;
  justify-content: center;
}

/* 预览区空状态 */
.empty-preview {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
  color: #9CA3C4;
  font-size: 12px;
}

.empty-preview p {
  margin: 0;
}

/* 简历内容预览 */
.resume-preview-content {
  width: 100%;
  height: 100%;
  overflow-y: auto;
  padding: 16px 18px;
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.resume-preview-content::-webkit-scrollbar {
  width: 5px;
}

.resume-preview-content::-webkit-scrollbar-thumb {
  background: var(--app-primary-light-7);
  border-radius: 3px;
}

.preview-header {
  text-align: center;
  padding-bottom: 10px;
  border-bottom: 1px dashed var(--app-primary-light-8);
}

.preview-name {
  font-size: 16px;
  font-weight: 700;
  color: #1E1E2D;
  margin: 0 0 4px;
}

.preview-position {
  font-size: 13px;
  color: var(--app-primary);
  font-weight: 500;
  margin: 0 0 2px;
}

.preview-meta {
  font-size: 11px;
  color: #9CA3C4;
  margin: 0;
}

.preview-section {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.section-title {
  font-size: 12px;
  font-weight: 700;
  color: var(--app-primary);
  margin: 4px 0 0;
  padding-bottom: 4px;
  border-bottom: 1px solid var(--app-primary-soft);
}

.preview-summary {
  font-size: 11px;
  color: #555770;
  line-height: 1.6;
  margin: 0;
  white-space: pre-line;
}

.preview-item {
  padding: 8px 10px;
  background: var(--app-primary-surface);
  border-radius: 6px;
  border-left: 3px solid var(--app-primary-light-7);
  margin-bottom: 4px;
}

.preview-item + .preview-item {
  margin-top: 4px;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2px;
}

.item-company {
  font-size: 12px;
  font-weight: 600;
  color: #1E1E2D;
}

.item-period {
  font-size: 10px;
  color: #9CA3C4;
  flex-shrink: 0;
  margin-left: 8px;
}

.item-role {
  font-size: 11px;
  color: var(--app-primary);
  margin: 2px 0;
}

.item-tasks {
  font-size: 11px;
  color: #555770;
  line-height: 1.6;
  margin: 4px 0 0;
  white-space: pre-line;
  word-break: break-word;
  overflow-wrap: break-word;
}

.preview-skills {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.skill-tag {
  display: inline-block;
  padding: 2px 8px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  border-radius: 10px;
  font-size: 11px;
  line-height: 1.5;
}

.location-dialog-description {
  margin: 0 0 16px;
  color: #606266;
  line-height: 1.6;
}

.jd-preview-content {
  padding-bottom: 16px;
}

.jd-list {
  margin: 6px 0 0;
  padding-left: 20px;
  color: #555770;
  font-size: 12px;
  line-height: 1.65;
}

.jd-list li + li {
  margin-top: 4px;
}

/* 操作按钮 — 统一纵列，所有按钮等宽、左对齐 */
.action-buttons {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
  margin-top: auto;
  padding-top: 4px;
}

.action-buttons .el-button {
  width: 80%;
  font-size: 11px;
  border-radius: 6px;
  padding: 5px 14px;
  height: auto;
  margin-left: 0;
  margin-right: 0;
  display: inline-flex;
  justify-content: center;
  text-align: center;
}

/* 下载按钮组 — 撑满宽度+左对齐，保证内部按钮与其他按钮左边缘一致 */
.download-group {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 6px;
  width: 100%;
}

/* 下载按钮 — fillColor=var(--app-primary) 实心紫 */
.action-buttons .el-button--primary {
  background: var(--app-primary) !important;
  border-color: var(--app-primary) !important;
}

/* 编辑内容 — fillColor=var(--app-primary-soft) 浅紫底 */
.btn-edit {
  background: var(--app-primary-soft) !important;
  color: var(--app-primary) !important;
  border: none !important;
}

/* 重新处理 — 白底紫边框 */
.btn-retry {
  background: transparent !important;
  border: 1px solid var(--app-primary) !important;
  color: var(--app-primary) !important;
}

/* 保存至JD库 — 白底紫边框 */
.btn-save {
  border: 1px solid var(--app-primary) !important;
  color: var(--app-primary) !important;
  background: transparent !important;
}

/* 空状态 */
.empty-state {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 6px;
  color: #9CA3C4;
  font-size: 12px;
}

/* 底部进度条 */
.bottom-bar {
  flex-shrink: 0;
}
/* Size controls by content so the upload frame never collapses around its children. */
.config-panel > * { grid-column: 1 / -1; min-width: 0; }
.config-panel.is-cv > .template-section,
.config-panel.is-cv > .language-section { grid-column: auto; }
.config-panel :deep(.el-input__inner) { height: 26px; font-size: 12px; }
.mode-tab, .toggle-btn { min-width: 0; white-space: normal; overflow-wrap: anywhere; }
.mode-tab { font-size: 11px; line-height: 1.3; padding: 6px 4px; }
.toggle-btn { padding-inline: 4px; }
.jd-preview { max-height: 64px; overflow-y: auto; }
.result-left > * { flex-shrink: 0; }
.action-buttons .el-button { min-height: 28px; white-space: normal; }
.action-buttons :deep(.el-button > span) { white-space: normal; overflow-wrap: anywhere; }
@media (max-height: 720px) {
  .config-panel { padding: 8px; gap: 5px; }
  .config-panel :deep(.file-upload) { min-height: 92px; padding: 8px; }
  .config-panel :deep(.upload-placeholder) {
    display: grid;
    grid-template-columns: 24px minmax(0, 1fr);
    gap: 4px 6px;
    width: 100%;
  }
  .config-panel :deep(.upload-icon), .config-panel :deep(.upload-title) { margin: 0; }
  .config-panel :deep(.upload-hint), .config-panel :deep(.upload-placeholder .el-button) {
    grid-column: 1 / -1; margin: 0; justify-self: center;
  }
  .config-panel :deep(.upload-title) { text-align: left; }
}
@media (max-width: 1100px) {
  .config-panel { width: 300px; }
  .result-panel { flex-direction: column; padding: 12px; gap: 12px; }
  .result-left { width: 100%; max-height: 42%; }
  .result-right { min-height: 0; }
}
@media (max-width: 760px) {
  .upload-page { height: auto; min-height: 100%; }
  .upload-layout { flex-direction: column; gap: 8px; flex: none; }
  .config-panel { width: 100%; overflow: visible; }
  .result-panel { flex: none; min-height: 150px; }
  .result-left { max-height: none; }
}
</style>
