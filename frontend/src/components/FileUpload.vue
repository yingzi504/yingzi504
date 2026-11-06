<template>
  <div
    class="file-upload"
    :class="{ 'is-dragover': isDragover, 'has-file': !!fileName }"
    @dragover.prevent="isDragover = true"
    @dragleave.prevent="isDragover = false"
    @drop.prevent="handleDrop"
  >
    <div v-if="!fileName" class="upload-placeholder">
      <div class="upload-icon">
        <el-icon :size="22"><Paperclip /></el-icon>
      </div>
      <p class="upload-title">{{ displayTitle }}</p>
      <p class="upload-hint">{{ displayHint }}</p>
      <el-button
        type="primary"
        size="small"
        :loading="isUploading"
        @click="triggerUpload"
      >
        {{ displayBtnText }}
      </el-button>
    </div>
    <div v-else class="upload-file-info">
      <el-icon :size="28"><Document /></el-icon>
      <div class="file-detail">
        <p class="file-name">{{ fileName }}</p>
        <p class="file-size">{{ fileSize }}</p>
      </div>
      <el-button type="danger" link @click="removeFile">✕</el-button>
    </div>
    <input
      ref="fileInputRef"
      type="file"
      :accept="accept"
      style="display: none"
      @change="handleSelect"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useI18n } from 'vue-i18n'
import { Document, Paperclip } from '@element-plus/icons-vue'

const { t } = useI18n()

const props = withDefaults(defineProps<{
  title?: string
  hint?: string
  btnText?: string
  accept?: string
  isUploading?: boolean
}>(), {
  title: '',
  hint: '',
  btnText: '',
  accept: '.pdf,.doc,.docx,.png,.jpg,.jpeg'
})

const displayTitle = computed(() => props.title || t('components.fileUpload.title'))
const displayHint = computed(() => props.hint || t('components.fileUpload.hint'))
const displayBtnText = computed(() => props.btnText || t('components.fileUpload.btnText'))

const emit = defineEmits<{
  (e: 'select', file: File): void
  (e: 'remove'): void
}>()

const fileInputRef = ref<HTMLInputElement>()
const isDragover = ref(false)
const selectedFile = ref<File | null>(null)

const fileName = computed(() => selectedFile.value?.name || '')
const fileSize = computed(() => {
  if (!selectedFile.value) return ''
  const size = selectedFile.value.size
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / (1024 * 1024)).toFixed(1)} MB`
})

function triggerUpload() {
  fileInputRef.value?.click()
}

function handleSelect(e: Event) {
  const target = e.target as HTMLInputElement
  const file = target.files?.[0]
  if (file) {
    selectedFile.value = file
    emit('select', file)
  }
}

function handleDrop(e: DragEvent) {
  isDragover.value = false
  const file = e.dataTransfer?.files?.[0]
  if (file) {
    selectedFile.value = file
    emit('select', file)
  }
}

function removeFile() {
  selectedFile.value = null
  if (fileInputRef.value) fileInputRef.value.value = ''
  emit('remove')
}
</script>

<style scoped>
.file-upload {
  border: 2px dashed #E8ECF3;
  border-radius: 8px;
  padding: 10px;
  text-align: center;
  transition: all 0.3s;
  background: #F5F6FA;
  min-height: 104px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  cursor: pointer;
}

.file-upload.is-dragover {
  border-color: var(--app-primary);
  background: var(--app-primary-soft);
}

.file-upload.has-file {
  border-style: solid;
  border-color: var(--app-primary);
  background: var(--app-primary-soft);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
}

.upload-icon {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  margin-bottom: 4px;
}

.upload-icon :deep(.el-icon) {
  transform: rotate(-40deg);
}

.upload-title {
  font-size: 13px;
  font-weight: 600;
  color: #5A5A7A;
  margin-bottom: 4px;
}

.upload-hint {
  font-size: 11px;
  color: #9CA3C4;
  margin-bottom: 6px;
}

.upload-or {
  font-size: 10px;
  color: #9CA3C4;
  margin-top: 8px;
}

.upload-file-info {
  display: flex;
  align-items: center;
  gap: 12px;
  width: 100%;
  padding: 0 8px;
}

.file-detail {
  flex: 1;
  min-width: 0;
  text-align: left;
}

.file-name {
  overflow-wrap: anywhere;
  font-size: 13px;
  font-weight: 600;
  color: #1E1E2D;
}

.file-size {
  font-size: 11px;
  color: #9CA3C4;
}
</style>
