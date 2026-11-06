<template>
  <el-tooltip
    :disabled="!steps || steps.length === 0"
    placement="top-start"
    :show-after="200"
  >
    <template #content>
      <div class="steps-tooltip">
        <div class="steps-title">{{ $t('components.progressBar.title') }}</div>
        <div
          v-for="(step, i) in steps"
          :key="i"
          class="step-item"
          :class="'step-' + step.status"
        >
          <span class="step-name">{{ stepName(step) }}</span>
          <span class="step-progress">{{ progressText(step.status) }}</span>
          <span v-if="step.duration" class="step-time">{{ formatDuration(step.duration) }}</span>
        </div>
      </div>
    </template>
    <div class="progress-bar-wrapper">
      <div class="progress-info">
        <span class="progress-label">{{ label }}</span>
        <span class="progress-percent">{{ percent }}%</span>
      </div>
      <div class="progress-track">
        <div
          class="progress-fill"
          :style="{ width: percent + '%' }"
          :class="{ 'is-error': status === 'failed', 'is-done': status === 'completed' }"
        />
      </div>
    </div>
  </el-tooltip>
</template>

<script setup lang="ts">
import { useI18n } from 'vue-i18n'
import type { ProcessingStep } from '@/types'

const { t } = useI18n()

defineProps<{
  label: string
  percent: number
  status?: string
  steps?: ProcessingStep[]
}>()

function stepName(step: { key?: string; name: string }): string {
  if (step.key) {
    const localized = t('components.progressBar.' + step.key)
    // 如果 key 在 locale 中存在，返回本地化名称；否则 fallback 到原始 name
    if (localized && !localized.startsWith('components.progressBar.')) {
      return localized
    }
  }
  return step.name
}

function progressText(status: string): string {
  switch (status) {
    case 'done':
    case 'completed': return '100%'
    case 'running':
    case 'in_progress': return t('components.progressBar.processing')
    case 'error':
    case 'failed': return t('components.progressBar.failed')
    case 'skipped': return t('components.progressBar.skipped')
    default: return '0%'
  }
}

function formatDuration(duration: string | number | null | undefined): string {
  if (duration == null) return ''
  if (typeof duration === 'number') {
    if (duration < 1000) return `${duration}ms`
    return `${(duration / 1000).toFixed(1)}s`
  }
  // 已经是字符串（如 "1.2s"），直接返回
  return String(duration)
}
</script>

<style scoped>
.progress-bar-wrapper {
  background: #fff;
  border: 1px solid #E8ECF3;
  border-radius: 6px;
  padding: 8px 12px;
}

.progress-info {
  display: flex;
  justify-content: flex-start;
  align-items: center;
  gap: 4px;
  margin-bottom: 4px;
}

.progress-label {
  font-size: 10px;
  color: #5A5A7A;
}

.progress-percent {
  font-size: 10px;
  font-weight: 600;
  color: var(--app-primary);
}

.progress-track {
  height: 4px;
  background: #E8ECF3;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: var(--app-primary);
  border-radius: 2px;
  transition: width 0.3s ease;
}

.progress-fill.is-error {
  background: #EF4444;
}

.progress-fill.is-done {
  background: #22C55E;
}

/* 步骤提示 */
.steps-tooltip {
  min-width: 180px;
}

.steps-title {
  font-size: 12px;
  font-weight: 600;
  margin-bottom: 8px;
  color: #fff;
}

.step-item {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 11px;
  color: #ccc;
  padding: 2px 0;
}

.step-item.step-done {
  color: #22C55E;
}

.step-item.step-running {
  color: var(--app-primary);
}

.step-item.step-error {
  color: #EF4444;
}

.step-name {
  margin-right: 6px;
}

.step-progress {
  font-size: 10px;
  color: #999;
  flex-shrink: 0;
}

.step-item.step-done .step-progress,
.step-item.step-completed .step-progress {
  color: #22C55E;
}

.step-item.step-running .step-progress,
.step-item.step-in_progress .step-progress {
  color: var(--app-primary);
}

.step-item.step-error .step-progress,
.step-item.step-failed .step-progress {
  color: #EF4444;
}

.step-time {
  color: #999;
  font-size: 10px;
}
</style>
