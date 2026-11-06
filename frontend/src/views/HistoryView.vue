<template>
  <div class="history-page">
    <div class="history-layout">
      <!-- 左侧筛选面板 -->
      <div class="filter-panel">
        <!-- 统计卡片 -->
        <div class="stats-grid">
          <StatCard icon="📊" :value="store.statistics?.totalCount || 0" :label="$t('history.totalProcessed')" />
          <StatCard icon="✅" :value="(store.statistics?.successRate || 0) + '%'" :label="$t('history.successRate')" />
          <StatCard icon="📅" :value="store.statistics?.monthlyCount || 0" :label="$t('history.thisMonth')" />
        </div>

        <!-- 搜索框 -->
        <el-input
          v-model="store.filterKeyword"
          :placeholder="$t('history.searchPlaceholder')"
          size="small"
          clearable
          @input="handleSearch"
        />

        <!-- 筛选条件 -->
        <div class="filter-section">
          <h4 class="filter-title">{{ $t('history.filter') }}</h4>

          <div class="filter-group">
            <label class="filter-label">{{ $t('history.processStatus') }}</label>
            <div class="filter-tags">
              <button
                v-for="s in statusOptions"
                :key="s.value"
                :class="['filter-tag', { active: store.filterStatus === s.value }]"
                @click="store.filterStatus = s.value; handleFilter()"
              >
                {{ s.label }}
              </button>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">{{ $t('history.outputLang') }}</label>
            <div class="filter-tags two-col">
              <button
                v-for="l in langOptions"
                :key="l.value"
                :class="['filter-tag', { active: store.filterLanguage === l.value }]"
                @click="store.filterLanguage = l.value; handleFilter()"
              >
                {{ l.label }}
              </button>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">{{ $t('history.outputContent') }}</label>
            <div class="filter-tags">
              <button
                v-for="o in outputOptions"
                :key="o.value"
                :class="['filter-tag', { active: store.filterOutputType === o.value }]"
                @click="store.filterOutputType = o.value; handleFilter()"
              >
                {{ o.label }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <!-- 右侧记录列表 -->
      <div class="record-panel">
        <h3 class="panel-title">{{ $t('history.records') }}</h3>

        <div v-loading="store.isLoading" class="record-list">
          <div
            v-for="record in store.records"
            :key="record.id"
            class="record-item"
          >
            <div class="record-main">
              <p class="record-name">{{ record.candidateName }}_{{ record.targetPosition }}</p>
              <p class="record-meta">
                {{ record.language }} · {{ record.templateType || $t('history.defaultTemplate') }} ·
                {{ record.duration || '—' }} · {{ record.createdAt }}
              </p>
              <div class="record-footer">
                <span
                  v-if="record.matchRate > 0"
                  class="match-text"
                  :class="{ 'match-high': record.matchRate >= 80, 'match-mid': record.matchRate >= 60 && record.matchRate < 80 }"
                >
                  {{ $t('history.matchRate', { rate: record.matchRate }) }}
                </span>
                <span v-else class="match-text match-none">{{ $t('history.noMatch') }}</span>
                <span
                  :class="['status-badge', record.status === 'success' ? 'status-success' : 'status-failed']"
                >
                  {{ record.status === 'success' ? $t('history.statusCompleted') : $t('history.statusFailed') }}
                </span>
              </div>
            </div>
            <div class="record-actions">
              <el-button v-if="record.status === 'success'" size="small" type="primary" @click="handleDownload(record)">
                {{ $t('history.download') }}
              </el-button>
              <el-button v-if="record.status === 'success'" size="small" class="btn-view" @click="handleView(record)">
                {{ $t('history.view') }}
              </el-button>
              <el-button v-if="record.status === 'failed'" size="small" type="danger" @click="handleRetry(record)">
                {{ $t('history.retry') }}
              </el-button>
            </div>
          </div>

          <!-- 空状态 -->
          <el-empty v-if="!store.isLoading && store.records.length === 0" :description="$t('history.empty')" />
        </div>

        <!-- 分页 -->
        <div v-if="store.total > store.pageSize" class="pagination-row">
          <span class="total-text">{{ $t('history.total', { count: store.total }) }}</span>
          <el-pagination
            v-model:current-page="store.currentPage"
            :page-size="store.pageSize"
            :total="store.total"
            small
            layout="prev, pager, next"
            @current-change="handlePageChange"
          />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useHistoryStore } from '@/stores/history'
import { useProcessingStore } from '@/stores/processing-advanced'
import { useRouter } from 'vue-router'
import StatCard from '@/components/StatCard.vue'

const { t } = useI18n()
const store = useHistoryStore()
const processingStore = useProcessingStore()
const router = useRouter()

const statusOptions = computed(() => [
  { label: t('history.all'), value: '' },
  { label: t('history.completed'), value: 'completed' },
  { label: t('history.failed'), value: 'failed' }
])

const langOptions = computed(() => [
  { label: t('history.all'), value: '' },
  { label: t('history.chinese'), value: 'zh' },
  { label: t('history.english'), value: 'en' },
  { label: t('history.cnEn'), value: 'zh-en' }
])

const outputOptions = computed(() => [
  { label: t('history.cv'), value: 'cv' },
  { label: t('history.jd'), value: 'jd' }
])

function buildParams() {
  return {
    status: store.filterStatus || undefined,
    language: store.filterLanguage || undefined,
    output_type: (store.filterOutputType || undefined) as 'cv' | 'jd' | undefined,
    keyword: store.filterKeyword || undefined,
    page: store.currentPage,
    pageSize: store.pageSize
  }
}

function handleFilter() {
  store.currentPage = 1
  store.fetchRecords(buildParams())
}

function handleSearch() {
  store.currentPage = 1
  store.fetchRecords(buildParams())
}

function handlePageChange(page: number) {
  store.currentPage = page
  store.fetchRecords(buildParams())
}

function handleDownload(record: any) {
  ElMessage.info('下载功能：' + record.id)
}

function handleView(record: any) {
  ElMessage.info('查看详情：' + record.id)
}

function handleRetry(_record: any) {
  processingStore.resetAll()
  router.push('/upload')
}

onMounted(() => {
  store.fetchStatistics()
  store.fetchRecords(buildParams())
})
</script>

<style scoped>
.history-page {
  height: 100%;
}

.history-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

/* 左侧筛选面板 */
.filter-panel {
  width: 377px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.stats-grid {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

/* 筛选区 */
.filter-section {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.filter-title {
  font-size: 12px;
  font-weight: 600;
  color: #1E1E2D;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.filter-label {
  font-size: 10px;
  font-weight: 600;
  color: #5A5A7A;
}

.filter-tags {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-tags.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
}

.filter-tag {
  padding: 5px 12px;
  border: none;
  border-radius: 6px;
  font-size: 10px;
  cursor: pointer;
  background: #F5F6FA;
  color: #5A5A7A;
  transition: all 0.2s;
  text-align: center;
}

.filter-tag.active {
  background: var(--app-primary);
  color: #fff;
  font-weight: 600;
}

/* 右侧记录面板 */
.record-panel {
  flex: 1;
  background: #fff;
  border-radius: 10px;
  padding: 16px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.04);
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #1E1E2D;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.record-list {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.record-item {
  background: #F5F6FA;
  border-radius: 8px;
  padding: 12px 14px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.record-main {
  flex: 1;
  min-width: 0;
}

.record-name {
  font-size: 12px;
  font-weight: 600;
  color: #1E1E2D;
  margin-bottom: 3px;
}

.record-meta {
  font-size: 10px;
  color: #9CA3C4;
  margin-bottom: 6px;
}

.record-footer {
  display: flex;
  align-items: center;
  gap: 8px;
}

.match-text {
  font-size: 11px;
  font-weight: 600;
}

.match-high { color: #22C55E; }
.match-mid { color: #F59E0B; }
.match-none { color: #9CA3C4; }

.status-badge {
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.status-success {
  background: #ECFDF5;
  color: #22C55E;
}

.status-failed {
  background: #FEF2F2;
  color: #EF4444;
}

.record-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.record-actions .el-button {
  font-size: 10px;
  height: 26px;
  padding: 0 10px;
  border-radius: 6px;
}

.btn-view {
  background: #F5F6FA !important;
  color: #5A5A7A !important;
  border: none !important;
}

/* 分页 */
.pagination-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding-top: 10px;
  flex-shrink: 0;
}

.total-text {
  font-size: 11px;
  color: #9CA3C4;
}

/* Compact controls, with independent scrolling for long result lists. */
.history-layout, .record-panel, .record-list { min-height: 0; }
.filter-panel { width: 320px; min-width: 0; min-height: 0; overflow-y: auto; gap: 8px; }
.filter-panel > * { flex-shrink: 0; }
.history-layout { gap: 12px; }
.record-panel { padding: 12px; }
.record-item { flex-shrink: 0; padding: 10px; flex-wrap: wrap; }
.filter-section, .filter-card, .upload-panel { padding: 10px; gap: 8px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; }
.stats-grid :deep(.stat-card) { padding: 8px 4px; flex-direction: column; gap: 4px; text-align: center; }
.stats-grid :deep(.stat-icon) { width: 24px; height: 24px; }
.record-actions, .template-actions { flex-wrap: wrap; gap: 6px; max-width: 100%; }
.record-actions .el-button, .template-actions .el-button { margin-left: 0; }
@media (max-width: 1100px) { .filter-panel { width: 280px; } }
@media (max-width: 760px) {
  .history-layout { flex-direction: column; height: auto; }
  .filter-panel { width: 100%; overflow: visible; }
  .record-panel { flex: none; }
  .record-list { max-height: 55dvh; }
}

</style>
