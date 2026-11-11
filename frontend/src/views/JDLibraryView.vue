<template>
  <div class="jd-page">
    <div class="jd-layout">
      <!-- 左侧筛选面板 -->
      <div class="jd-filter-panel">
        <!-- 统计卡片 -->
        <div class="jd-stats-row">
          <StatCard icon="💼" :value="store.total" :label="$t('jdLibrary.totalCount')" />
          <StatCard icon="🔧" :value="categoryCount('汽车技术')" :label="$t('jdLibrary.catAutoTech')" />
          <StatCard icon="📊" :value="categoryCount('产品管理')" :label="$t('jdLibrary.catProductMgmt')" />
          <StatCard icon="💻" :value="categoryCount('软件研发')" :label="$t('jdLibrary.catSoftwareDev')" />
        </div>

        <!-- 搜索 -->
        <el-input
          v-model="store.keyword"
          :placeholder="$t('jdLibrary.searchPlaceholder')"
          size="small"
          clearable
          @input="handleSearch"
        />

        <!-- 筛选条件 -->
        <div class="filter-card">
          <h4 class="filter-title">{{ $t('jdLibrary.filter') }}</h4>

          <div class="filter-group">
            <label class="filter-label">{{ $t('jdLibrary.jobCategory') }}</label>
            <div class="filter-grid">
              <button
                v-for="c in categoryOptions"
                :key="c.value"
                :class="['filter-tag', { active: store.activeCategory === c.value }]"
                @click="store.activeCategory = c.value; handleFilter()"
              >
                {{ c.label }}
              </button>
            </div>
          </div>

          <div class="filter-group">
            <label class="filter-label">{{ $t('jdLibrary.jdLang') }}</label>
            <div class="filter-grid">
              <button
                v-for="l in langOptions"
                :key="l.value"
                :class="['filter-tag', { active: store.activeLanguage === l.value }]"
                @click="store.activeLanguage = l.value; handleFilter()"
              >
                {{ l.label }}
              </button>
            </div>
          </div>

          <!-- 上传新JD -->
          <el-button type="primary" size="small" class="btn-new-jd" @click="showAddDialog = true">
            {{ $t('jdLibrary.uploadNew') }}
          </el-button>
        </div>

        <!-- 热门岗位 -->
        <div class="hot-section">
          <h4 class="filter-title">{{ $t('jdLibrary.hotJobs') }}</h4>
          <div class="hot-tags">
            <span v-for="tag in hotTags" :key="tag" class="hot-tag">{{ tag }}</span>
          </div>
        </div>
      </div>

      <!-- 右侧JD列表 -->
      <div class="jd-list-panel">
        <div class="panel-header">
          <h3 class="panel-title">{{ $t('jdLibrary.listTitle') }}</h3>
          <el-button type="primary" size="small" @click="showAddDialog = true">{{ $t('jdLibrary.addNew') }}</el-button>
        </div>

        <div v-loading="store.isLoading" class="jd-items">
          <div
            v-for="jd in store.jds"
            :key="jd.id"
            class="jd-card"
          >
            <p class="jd-position">{{ jd.position }}</p>
            <div class="jd-meta">
              <span class="jd-dept">{{ jd.department }}</span>
              <span class="jd-lang">{{ jd.language }}</span>
              <span class="jd-status" :class="{ active: jd.active !== false }">
                {{ jd.active !== false ? $t('templates.enabled') : $t('templates.disabled') }}
              </span>
            </div>
            <p class="jd-keywords">
              🔑 {{ (jd.tags || []).join(', ') || jd.position }}
            </p>
          </div>

          <el-empty v-if="!store.isLoading && store.jds.length === 0" :description="$t('jdLibrary.empty')" />
        </div>
      </div>
    </div>

    <!-- 新增JD对话框 -->
    <el-dialog v-model="showAddDialog" :title="$t('jdLibrary.dialogTitle')" width="500px">
      <el-form :model="newJDForm" label-width="80px" label-position="top" size="small">
        <el-form-item :label="$t('jdLibrary.positionLabel')" required>
          <el-input v-model="newJDForm.position" :placeholder="$t('jdLibrary.positionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('jdLibrary.deptLabel')" required>
          <el-select v-model="newJDForm.department" :placeholder="$t('jdLibrary.deptPlaceholder')" style="width: 100%">
            <el-option v-for="d in deptOptions" :key="d" :label="d" :value="d" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('jdLibrary.catLabel')" required>
          <el-select v-model="newJDForm.category" :placeholder="$t('jdLibrary.catPlaceholder')" style="width: 100%">
            <el-option v-for="c in categoryOptions.filter(c => c.value !== '')" :key="c.value" :label="c.label" :value="c.value" />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('jdLibrary.langLabel')" required>
          <el-radio-group v-model="newJDForm.language">
            <el-radio value="zh">{{ $t('upload.chinese') }}</el-radio>
            <el-radio value="en">{{ $t('upload.english') }}</el-radio>
          </el-radio-group>
        </el-form-item>
        <el-form-item :label="$t('jdLibrary.contentLabel')" required>
          <el-input v-model="newJDForm.content" type="textarea" :rows="5" :placeholder="$t('jdLibrary.contentPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('jdLibrary.tagsLabel')">
          <el-input v-model="newJDForm.tagsStr" :placeholder="$t('jdLibrary.tagsPlaceholder')" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">{{ $t('jdLibrary.cancel') }}</el-button>
        <el-button type="primary" :disabled="!newJDForm.position || !newJDForm.content" @click="handleAddJD">
          {{ $t('jdLibrary.confirm') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage } from 'element-plus'
import { useJDStore } from '@/stores/jd'
import StatCard from '@/components/StatCard.vue'

const { t } = useI18n()
const store = useJDStore()
const showAddDialog = ref(false)

const newJDForm = reactive({
  position: '',
  department: '',
  category: '',
  language: 'zh',
  content: '',
  tagsStr: ''
})

const categoryOptions = computed(() => [
  { label: t('history.all'), value: '' },
  { label: t('jdLibrary.catAutoTech'), value: '汽车技术' },
  { label: t('jdLibrary.catProductMgmt'), value: '产品管理' },
  { label: t('jdLibrary.catSoftwareDev'), value: '软件研发' }
])

const langOptions = computed(() => [
  { label: t('history.all'), value: '' },
  { label: t('upload.chinese'), value: 'zh' },
  { label: t('upload.english'), value: 'en' }
])

const deptOptions = computed(() => [
  t('jdLibrary.dept1'),
  t('jdLibrary.dept2'),
  t('jdLibrary.dept3'),
  t('jdLibrary.dept4'),
  t('jdLibrary.dept5')
])

const hotTags = computed(() => [1, 2, 3, 4, 5, 6].map(index => t(`jdLibrary.hotTag${index}`)))

function categoryCount(cat: string): number {
  return store.jds.filter(j => j.category === cat).length
}

function handleSearch() {
  store.fetchJDs({ keyword: store.keyword, category: store.activeCategory, language: store.activeLanguage })
}

function handleFilter() {
  store.fetchJDs({ category: store.activeCategory, language: store.activeLanguage, keyword: store.keyword })
}

async function handleAddJD() {
  try {
    await store.addJD({
      position: newJDForm.position,
      department: newJDForm.department,
      language: newJDForm.language,
      category: newJDForm.category,
      content: newJDForm.content,
      tags: newJDForm.tagsStr.split(',').map(t => t.trim()).filter(Boolean)
    })
    ElMessage.success(t('jdLibrary.createSuccess'))
    showAddDialog.value = false
    // 重置表单
    newJDForm.position = ''
    newJDForm.department = ''
    newJDForm.category = ''
    newJDForm.language = 'zh'
    newJDForm.content = ''
    newJDForm.tagsStr = ''
  } catch {
    ElMessage.error(t('jdLibrary.createFailed'))
  }
}

onMounted(() => {
  store.fetchJDs()
})
</script>

<style scoped>
.jd-page {
  height: 100%;
}

.jd-layout {
  display: flex;
  gap: 16px;
  height: 100%;
}

/* 左侧筛选面板 */
.jd-filter-panel {
  width: 377px;
  flex-shrink: 0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.jd-stats-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 8px;
}

/* 筛选卡片 */
.filter-card {
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 12px;
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

.filter-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 6px;
}

.filter-tag {
  padding: 5px 0;
  border: none;
  border-radius: 6px;
  font-size: 10px;
  cursor: pointer;
  background: #F1F3F8;
  color: #5A5A7A;
  transition: all 0.2s;
  text-align: center;
}

.filter-tag.active {
  background: var(--app-primary);
  color: #fff;
  font-weight: 600;
}

.btn-new-jd {
  width: 100%;
  font-size: 11px;
  border-radius: 6px;
}

/* 热门岗位 */
.hot-section {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.hot-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.hot-tag {
  font-size: 10px;
  padding: 4px 10px;
  border-radius: 12px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
  cursor: pointer;
  transition: all 0.2s;
}

.hot-tag:hover {
  background: var(--app-primary);
  color: #fff;
}

/* 右侧JD列表 */
.jd-list-panel {
  flex: 1;
  background: #fff;
  border-radius: 10px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-shrink: 0;
}

.panel-title {
  font-size: 13px;
  font-weight: 600;
  color: #1E1E2D;
}

.jd-items {
  flex: 1;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.jd-card {
  background: #fff;
  border-radius: 8px;
  padding: 12px 14px;
}

.jd-position {
  font-size: 12px;
  font-weight: 600;
  color: #1E1E2D;
  margin-bottom: 4px;
}

.jd-meta {
  display: flex;
  gap: 6px;
  align-items: center;
  margin-bottom: 4px;
}

.jd-dept {
  font-size: 9px;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--app-primary-soft);
  color: var(--app-primary);
}

.jd-lang {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  background: #EFF6FF;
  color: #3B82F6;
}

.jd-status {
  font-size: 9px;
  padding: 2px 6px;
  border-radius: 4px;
  font-weight: 600;
}

.jd-status.active {
  background: #ECFDF5;
  color: #22C55E;
}

.jd-status:not(.active) {
  background: #FEF2F2;
  color: #EF4444;
}

.jd-keywords {
  font-size: 10px;
  color: #5A5A7A;
}

/* Compact controls, with independent scrolling for long result lists. */
.jd-layout, .jd-list-panel, .jd-items { min-height: 0; }
.jd-filter-panel { width: 320px; min-width: 0; min-height: 0; overflow-y: auto; gap: 8px; }
.jd-filter-panel > * { flex-shrink: 0; }
.jd-layout { gap: 12px; }
.jd-list-panel { padding: 12px; }
.jd-card { flex-shrink: 0; padding: 10px; flex-wrap: wrap; }
.filter-section, .filter-card, .upload-panel { padding: 10px; gap: 8px; }
.stats-grid { display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 4px; }
.stats-grid :deep(.stat-card) { padding: 8px 4px; flex-direction: column; gap: 4px; text-align: center; }
.stats-grid :deep(.stat-icon) { width: 24px; height: 24px; }
.record-actions, .template-actions { flex-wrap: wrap; gap: 6px; max-width: 100%; }
.record-actions .el-button, .template-actions .el-button { margin-left: 0; }
@media (max-width: 1100px) { .jd-filter-panel { width: 280px; } }
@media (max-width: 760px) {
  .jd-layout { flex-direction: column; height: auto; }
  .jd-filter-panel { width: 100%; overflow: visible; }
  .jd-list-panel { flex: none; }
  .jd-items { max-height: 55dvh; }
}

</style>
