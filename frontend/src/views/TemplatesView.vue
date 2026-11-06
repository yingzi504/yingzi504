<template>
  <div class="templates-page">
    <!-- 双栏布局：左侧面板 + 右侧模板列表 -->
    <div class="templates-layout">
      <!-- 左侧面板（统计卡片 + 上传白框） -->
      <div class="left-panel">
        <!-- 统计卡片 — 白框外 -->
        <div class="stats-grid">
          <StatCard icon="📑" :value="totalCount" :label="$t('templates.totalCount')" />
          <StatCard icon="📄" :value="portraitCount" :label="$t('templates.verticalCount')" />
          <StatCard icon="📃" :value="landscapeCount" :label="$t('templates.horizontalCount')" />
        </div>

        <!-- 上传白框 -->
        <div class="upload-panel">
          <h3 class="panel-title">{{ $t('templates.uploadNewVersion') }}</h3>
          <FileUpload
            :title="$t('templates.dragFileHere')"
            :hint="$t('templates.clickToUpload')"
            :btn-text="$t('templates.selectFile')"
            accept=".pptx,.ppt"
            @select="handleUploadNew"
          />
          <el-button
            type="primary"
            size="small"
            class="btn-new-template"
            @click="showNewTemplateDialog = true"
          >
            {{ $t('templates.uploadNewTemplate') }}
          </el-button>
        </div>
      </div>

      <!-- 右侧模板列表 -->
      <div class="template-list-panel">
        <h3 class="panel-title">{{ $t('templates.templateList') }}</h3>

        <div v-loading="store.isLoading" class="template-items">
          <div
            v-for="template in store.templates"
            :key="template.id"
            class="template-card"
          >
            <!-- 图标 + 状态徽章 -->
            <div class="template-icon-area">
              <div class="template-icon">
                {{ template.category === 'portrait' ? '📄' : '📃' }}
              </div>
              <span class="status-badge" :class="{ inactive: !template.active }">
                {{ template.active !== false ? $t('templates.enabled') : $t('templates.disabled') }}
              </span>
            </div>

            <!-- 模板信息 -->
            <div class="template-info">
              <p class="template-name">{{ template.name }}</p>
              <p class="template-meta">v{{ template.version }} · 更新于 {{ template.updatedAt }}</p>
              <div class="template-tags">
                <span class="tpl-tag">{{ template.category === 'portrait' ? $t('templates.vertical') : $t('templates.horizontal') }}</span>
                <span class="tpl-tag lang-tag">{{ template.language }}</span>
              </div>
            </div>

            <!-- 操作按钮 -->
            <div class="template-actions">
              <el-button size="small" class="btn-preview" @click="handlePreview(template)">{{ $t('templates.preview') }}</el-button>
              <el-button size="small" class="btn-download" @click="handleDownload(template)">{{ $t('templates.download') }}</el-button>
              <el-button size="small" type="primary" @click="triggerUpdate(template)">{{ $t('templates.updateVersion') }}</el-button>
            </div>
          </div>

          <el-empty v-if="!store.isLoading && store.templates.length === 0" :description="$t('templates.empty')" />
        </div>
      </div>
    </div>

    <!-- 新建模板对话框 -->
    <el-dialog v-model="showNewTemplateDialog" :title="$t('templates.dialogTitle')" width="420px">
      <FileUpload
        :title="$t('templates.dialogInnerTitle')"
        :hint="$t('templates.dialogHint')"
        :btn-text="$t('templates.selectFile')"
        accept=".pptx,.ppt"
        @select="handleNewTemplateFile"
      />
      <template #footer>
        <el-button @click="showNewTemplateDialog = false">{{ $t('templates.dialogCancel') }}</el-button>
        <el-button type="primary" :disabled="!pendingTemplateFile" @click="confirmNewTemplate">
          {{ $t('templates.dialogConfirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useTemplateStore } from '@/stores/template'
import type { TemplateItem } from '@/types'
import StatCard from '@/components/StatCard.vue'
import FileUpload from '@/components/FileUpload.vue'

const { t } = useI18n()
const store = useTemplateStore()

const showNewTemplateDialog = ref(false)
const pendingTemplateFile = ref<File | null>(null)

const totalCount = computed(() => store.templates.length)
const portraitCount = computed(() => store.templates.filter(t => t.category === 'portrait').length)
const landscapeCount = computed(() => store.templates.filter(t => t.category === 'landscape').length)

function handlePreview(template: TemplateItem) {
  ElMessage.info('预览功能：' + template.name)
}

function handleDownload(template: TemplateItem) {
  ElMessage.info('下载功能：' + template.name)
}

async function handleUploadNew(file: File) {
  try {
    await store.addTemplate(file)
    ElMessage.success(t('templates.uploadSuccess'))
  } catch {
    ElMessage.error(t('templates.uploadFailed'))
  }
}

function triggerUpdate(template: TemplateItem) {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.pptx,.ppt'
  input.onchange = async (e) => {
    const file = (e.target as HTMLInputElement).files?.[0]
    if (file) {
      try {
        await store.upgradeTemplate(template.id, file)
        ElMessage.success(t('templates.updateSuccess'))
      } catch {
        ElMessage.error(t('templates.updateFailed'))
      }
    }
  }
  input.click()
}

function handleNewTemplateFile(file: File) {
  pendingTemplateFile.value = file
}

async function confirmNewTemplate() {
  if (!pendingTemplateFile.value) return
  try {
    await store.addTemplate(pendingTemplateFile.value)
    ElMessage.success(t('templates.createSuccess'))
    showNewTemplateDialog.value = false
    pendingTemplateFile.value = null
  } catch {
    ElMessage.error(t('templates.createFailed'))
  }
}

onMounted(() => {
  store.fetchTemplates()
})
</script>

<style scoped>
.templates-page {
  height: 100%;
  display: flex;
  flex-direction: column;
  gap: 14px;
}

/* 统计卡片 — 纵向堆叠，参照历史记录界面 */
.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 双栏布局 */
.templates-layout {
  display: flex;
  gap: 16px;
  flex: 1;
  min-height: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #1E1E2D;
  margin: 0 0 12px;
}

/* 左侧面板 — 无背景，纵向排列子项 */
.left-panel {
  width: 377px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

/* 上传白框 */
.upload-panel {
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
}

.btn-new-template {
  width: 100%;
  margin-top: 14px;
  font-size: 11px;
  border-radius: 6px;
}

/* 右侧模板列表 */
.template-list-panel {
  flex: 1;
  min-width: 0;
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
}

.template-items {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.template-card {
  background: #fff;
  border: 1px solid #E0E3EA;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  align-items: flex-start;
  gap: 12px;
}

/* 图标 + 状态徽章 */
.template-icon-area {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.template-icon {
  width: 36px;
  height: 36px;
  background: var(--app-primary-soft);
  border-radius: 8px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 20px;
}

.status-badge {
  font-size: 8px;
  font-weight: 600;
  padding: 1px 8px;
  border-radius: 4px;
  background: #ECFDF5;
  color: #22C55E;
  white-space: nowrap;
}

.status-badge.inactive {
  background: #FEF2F2;
  color: #EF4444;
}

/* 模板信息 */
.template-info {
  flex: 1;
  min-width: 0;
}

.template-name {
  font-size: 12px;
  font-weight: 600;
  color: #1E1E2D;
  margin-bottom: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.template-meta {
  font-size: 10px;
  color: #9CA3C4;
  margin-bottom: 6px;
}

.template-tags {
  display: flex;
  gap: 6px;
}

.tpl-tag {
  font-size: 9px;
  padding: 2px 10px;
  border-radius: 4px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  font-weight: 600;
}

.lang-tag {
  background: #EFF6FF;
  color: #3B82F6;
}

/* 操作按钮 */
.template-actions {
  display: flex;
  gap: 6px;
  flex-shrink: 0;
  align-items: flex-start;
}

.template-actions .el-button {
  font-size: 10px;
  height: 26px;
  padding: 0 12px;
  border-radius: 5px;
}

.template-actions .el-button--primary {
  font-size: 10px;
}

.btn-preview,
.btn-download {
  background: #F1F3F8 !important;
  color: #5A5A7A !important;
  border: none !important;
}

/* Compact controls, with independent scrolling for long result lists. */
.templates-layout, .template-list-panel, .template-items { min-height: 0; }
.left-panel { width: 320px; min-width: 0; min-height: 0; overflow-y: auto; gap: 8px; }
.left-panel > * { flex-shrink: 0; }
.templates-layout { gap: 12px; }
.template-list-panel { padding: 12px; }
.template-card { flex-shrink: 0; padding: 10px; flex-wrap: wrap; }
.filter-section, .filter-card, .upload-panel { padding: 10px; gap: 8px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; }
.stats-grid :deep(.stat-card) { padding: 8px 4px; flex-direction: column; gap: 4px; text-align: center; }
.stats-grid :deep(.stat-icon) { width: 24px; height: 24px; }
.record-actions, .template-actions { flex-wrap: wrap; gap: 6px; max-width: 100%; }
.record-actions .el-button, .template-actions .el-button { margin-left: 0; }
@media (max-width: 1100px) { .left-panel { width: 280px; } }
@media (max-width: 760px) {
  .templates-layout { flex-direction: column; height: auto; }
  .left-panel { width: 100%; overflow: visible; }
  .template-list-panel { flex: none; }
  .template-items { max-height: 55dvh; }
}

</style>
