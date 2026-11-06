<template>
  <div class="cv-library-page">
    <aside class="department-rail">
      <div class="rail-heading">
        <span class="rail-eyebrow">{{ $t('cvLibrary.archiveIndex') }}</span>
        <strong>{{ $t('cvLibrary.departmentDirectory') }}</strong>
        <p>{{ $t('cvLibrary.departmentHint') }}</p>
      </div>

      <button
        class="department-item"
        :class="{ active: selectedDepartment === '' }"
        @click="selectDepartment('')"
      >
        <span>{{ $t('cvLibrary.allDepartments') }}</span>
        <b>{{ allCount }}</b>
      </button>

      <div class="department-list">
        <button
          v-for="entry in departments"
          :key="entry.code"
          class="department-item"
          :class="{ active: selectedDepartment === entry.code }"
          @click="selectDepartment(entry.code)"
        >
          <span>{{ entry.code }}</span>
          <b>{{ entry.count }}</b>
        </button>
        <button
          v-if="unclassified > 0"
          class="department-item muted"
          :class="{ active: selectedDepartment === '__unclassified__' }"
          @click="selectDepartment('__unclassified__')"
        >
          <span>{{ $t('cvLibrary.unclassified') }}</span>
          <b>{{ unclassified }}</b>
        </button>
      </div>
    </aside>

    <section class="library-workspace">
      <div class="library-toolbar">
        <div>
          <span class="selection-label">{{ selectedDepartmentLabel }}</span>
          <h2>{{ $t('cvLibrary.completedCVs') }}</h2>
        </div>
        <el-input
          v-model="positionKeyword"
          class="position-search"
          clearable
          :prefix-icon="Search"
          :placeholder="$t('cvLibrary.positionPlaceholder')"
          @keyup.enter="search"
          @clear="search"
        >
          <template #append>
            <el-button @click="search">{{ $t('cvLibrary.search') }}</el-button>
          </template>
        </el-input>
      </div>

      <div class="result-summary">
        <span>{{ $t('cvLibrary.resultCount', { count: total }) }}</span>
        <span>{{ $t('cvLibrary.autoArchiveNote') }}</span>
      </div>

      <div v-loading="loading" class="archive-table-wrap">
        <table v-if="items.length" class="archive-table">
          <thead>
            <tr>
              <th>{{ $t('cvLibrary.file') }}</th>
              <th>{{ $t('cvLibrary.department') }}</th>
              <th>{{ $t('cvLibrary.position') }}</th>
              <th>{{ $t('cvLibrary.completedAt') }}</th>
              <th class="actions-column">{{ $t('cvLibrary.actions') }}</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="item in items" :key="item.id">
              <td>
                <div class="file-cell">
                  <span class="file-mark"><el-icon><Document /></el-icon></span>
                  <span>
                    <strong>{{ displayName(item) }}</strong>
                    <small>{{ availableFormats(item) }}</small>
                  </span>
                </div>
              </td>
              <td><span class="department-chip">{{ item.department || $t('cvLibrary.unclassified') }}</span></td>
              <td><span class="position-value">{{ item.position || $t('cvLibrary.noPosition') }}</span></td>
              <td><time :datetime="item.updated_at">{{ formatDate(item.updated_at) }}</time></td>
              <td class="actions-column">
                <el-button
                  v-for="file in downloadFormats(item)"
                  :key="file.format"
                  text
                  type="primary"
                  :icon="Download"
                  :loading="downloading === `${item.id}:${file.format}`"
                  @click="download(item, file.format)"
                >
                  {{ file.format.toUpperCase() }}
                </el-button>
              </td>
            </tr>
          </tbody>
        </table>

        <el-empty
          v-else-if="!loading"
          :description="positionKeyword ? $t('cvLibrary.noSearchResults') : $t('cvLibrary.empty')"
        >
          <el-button v-if="positionKeyword" type="primary" plain @click="clearSearch">
            {{ $t('cvLibrary.clearSearch') }}
          </el-button>
        </el-empty>
      </div>

      <el-pagination
        v-if="total > pageSize"
        v-model:current-page="page"
        class="library-pagination"
        background
        layout="prev, pager, next"
        :page-size="pageSize"
        :total="total"
        @current-change="load"
      />
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { Document, Download, Search } from '@element-plus/icons-vue'
import {
  downloadCVLibraryFile,
  getCVLibrary,
  type CVLibraryFile,
  type CVLibraryItem,
  type DepartmentCount
} from '@/api/cv-library'

const { t, locale } = useI18n()
const items = ref<CVLibraryItem[]>([])
const departments = ref<DepartmentCount[]>([])
const unclassified = ref(0)
const total = ref(0)
const allCount = ref(0)
const page = ref(1)
const pageSize = 20
const selectedDepartment = ref('')
const positionKeyword = ref('')
const appliedPosition = ref('')
const loading = ref(false)
const downloading = ref('')

const selectedDepartmentLabel = computed(() => {
  if (selectedDepartment.value === '__unclassified__') return t('cvLibrary.unclassified')
  return selectedDepartment.value || t('cvLibrary.allDepartments')
})

async function load() {
  loading.value = true
  try {
    const response = await getCVLibrary({
      department: selectedDepartment.value,
      position: appliedPosition.value,
      page: page.value,
      page_size: pageSize
    })
    items.value = response.data
    departments.value = response.departments
    unclassified.value = response.unclassified
    total.value = response.total
    if (!selectedDepartment.value && !appliedPosition.value) {
      allCount.value = response.total
    } else {
      allCount.value = response.departments.reduce((sum, entry) => sum + entry.count, 0) + response.unclassified
    }
  } catch {
    ElMessage.error(t('cvLibrary.loadFailed'))
  } finally {
    loading.value = false
  }
}

function selectDepartment(department: string) {
  selectedDepartment.value = department
  page.value = 1
  void load()
}

function search() {
  appliedPosition.value = positionKeyword.value.trim()
  page.value = 1
  void load()
}

function clearSearch() {
  positionKeyword.value = ''
  appliedPosition.value = ''
  page.value = 1
  void load()
}

function displayName(item: CVLibraryItem) {
  return item.files.find(file => file.available)?.name || item.name || item.id
}

function availableFormats(item: CVLibraryItem) {
  return item.files.filter(file => file.available).map(file => file.format.toUpperCase()).join(' · ')
}

function downloadFormats(item: CVLibraryItem): CVLibraryFile[] {
  const available = item.files.filter(file => file.available)
  // PDF can be generated on demand from an archived PPTX, so expose the
  // action even for older records that predate PDF archiving.
  if (available.some(file => file.format === 'pptx') && !available.some(file => file.format === 'pdf')) {
    const pptx = item.files.find(file => file.format === 'pptx')!
    return [...available, { ...pptx, format: 'pdf' as const }]
  }
  return available
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat(locale.value === 'zh-CN' ? 'zh-CN' : 'en', {
    year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit'
  }).format(new Date(value))
}

async function download(item: CVLibraryItem, format: 'pptx' | 'pdf') {
  downloading.value = `${item.id}:${format}`
  try {
    const blob = await downloadCVLibraryFile(item.id, format)
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = item.files.find(file => file.format === format)?.name || `CV.${format}`
    link.click()
    URL.revokeObjectURL(url)
  } catch {
    ElMessage.error(t('cvLibrary.downloadFailed'))
  } finally {
    downloading.value = ''
  }
}

onMounted(load)
</script>

<style scoped>
.cv-library-page { display: grid; grid-template-columns: 248px minmax(0, 1fr); gap: 14px; height: 100%; min-height: 0; color: #1e1e2d; }
.department-rail, .library-workspace { min-height: 0; background: #fff; border: 1px solid #e5e7ef; border-radius: 12px; }
.department-rail { display: flex; flex-direction: column; overflow: hidden; }
.rail-heading { padding: 20px 18px 16px; border-bottom: 1px solid #ececf3; background: linear-gradient(145deg, #fbf9ff, #f4f0fb); }
.rail-eyebrow { display: block; margin-bottom: 7px; color: var(--app-primary); font-size: 9px; font-weight: 700; letter-spacing: .16em; text-transform: uppercase; }
.rail-heading strong { display: block; font-size: 16px; line-height: 1.4; }
.rail-heading p { margin: 6px 0 0; color: #88889a; font-size: 10px; line-height: 1.6; }
.department-list { flex: 1; min-height: 0; overflow-y: auto; padding: 5px 0 12px; }
.department-item { display: flex; align-items: center; justify-content: space-between; width: 100%; min-height: 36px; padding: 7px 16px; border: 0; border-left: 3px solid transparent; background: transparent; color: #5e5e73; font: inherit; font-size: 11px; cursor: pointer; text-align: left; }
.department-item:first-of-type { margin-top: 5px; }
.department-item:hover { background: #f7f5fb; color: #342842; }
.department-item.active { border-left-color: var(--app-primary); background: var(--app-primary-soft); color: var(--app-primary-dark); font-weight: 600; }
.department-item b { min-width: 24px; padding: 2px 6px; border-radius: 10px; background: #f0eff4; color: #858397; font-size: 9px; font-weight: 600; text-align: center; }
.department-item.active b { background: #fff; color: var(--app-primary); }
.department-item.muted { color: #9997a5; }
.library-workspace { display: flex; flex-direction: column; overflow: hidden; }
.library-toolbar { display: flex; align-items: center; justify-content: space-between; gap: 22px; padding: 18px 20px 14px; }
.selection-label { color: var(--app-primary); font-size: 10px; font-weight: 700; letter-spacing: .08em; }
.library-toolbar h2 { margin: 3px 0 0; font-size: 18px; font-weight: 600; }
.position-search { width: min(430px, 48%); }
.result-summary { display: flex; justify-content: space-between; gap: 12px; padding: 8px 20px; border-top: 1px solid #eeeef4; border-bottom: 1px solid #eeeef4; background: #fafafe; color: #8a8998; font-size: 10px; }
.archive-table-wrap { flex: 1; min-height: 0; overflow: auto; }
.archive-table { width: 100%; border-collapse: collapse; table-layout: fixed; }
.archive-table th { position: sticky; top: 0; z-index: 1; padding: 10px 14px; background: #f6f5f9; color: #79788a; font-size: 10px; font-weight: 600; text-align: left; }
.archive-table td { padding: 12px 14px; border-bottom: 1px solid #efeff4; color: #57566a; font-size: 11px; vertical-align: middle; }
.archive-table tr:hover td { background: #fcfbfe; }
.archive-table th:nth-child(1) { width: 31%; }
.archive-table th:nth-child(2) { width: 12%; }
.archive-table th:nth-child(3) { width: 21%; }
.archive-table th:nth-child(4) { width: 18%; }
.file-cell { display: flex; align-items: center; gap: 10px; min-width: 0; }
.file-cell > span:last-child { min-width: 0; }
.file-mark { display: grid; place-items: center; flex-shrink: 0; width: 32px; height: 38px; border: 1px solid #ded7e8; border-radius: 5px 5px 8px 5px; background: var(--app-primary-soft); color: var(--app-primary); font-size: 16px; }
.file-cell strong { display: block; overflow: hidden; color: #2f2e3c; font-size: 11px; font-weight: 600; text-overflow: ellipsis; white-space: nowrap; }
.file-cell small { display: block; margin-top: 4px; color: #9b99a8; font-size: 9px; letter-spacing: .06em; }
.department-chip { display: inline-block; padding: 3px 8px; border: 1px solid #ddd4e8; border-radius: 4px; background: #f8f5fb; color: var(--app-primary-dark); font-weight: 600; }
.position-value { color: #383747; }
.actions-column { text-align: right !important; }
.actions-column .el-button + .el-button { margin-left: 2px; }
.library-pagination { justify-content: flex-end; padding: 12px 18px; border-top: 1px solid #eeeef4; }
@media (max-width: 900px) {
  .cv-library-page { grid-template-columns: 190px minmax(0, 1fr); }
  .library-toolbar { align-items: stretch; flex-direction: column; gap: 10px; }
  .position-search { width: 100%; }
  .archive-table { min-width: 780px; }
}
@media (max-width: 760px) {
  .cv-library-page { display: flex; flex-direction: column; height: auto; }
  .department-rail { max-height: 250px; }
  .library-workspace { min-height: 520px; }
  .result-summary { flex-direction: column; }
}
@media (prefers-reduced-motion: reduce) { .department-item { scroll-behavior: auto; } }
</style>
