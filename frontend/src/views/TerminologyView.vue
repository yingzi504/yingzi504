<template>
  <div class="terminology-page">
    <div class="metric-strip">
      <div v-for="metric in metrics" :key="metric.label" class="metric-item">
        <div class="metric-icon" :class="metric.tone">
          <el-icon><component :is="metric.icon" /></el-icon>
        </div>
        <div>
          <p class="metric-value">{{ metric.value }}</p>
          <p class="metric-label">{{ metric.label }}</p>
        </div>
      </div>
    </div>

    <section class="terms-workspace">
      <div class="toolbar">
        <div class="filter-row">
          <el-input
            v-model="keyword"
            :prefix-icon="Search"
            :placeholder="$t('terminology.searchPlaceholder')"
            clearable
            class="search-input"
          />
          <el-select v-model="categoryFilter" :placeholder="$t('terminology.category')" class="filter-select">
            <el-option v-for="option in categoryOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
          <el-select v-model="statusFilter" :placeholder="$t('terminology.status')" class="filter-select status-select">
            <el-option v-for="option in statusOptions" :key="option.value" :label="option.label" :value="option.value" />
          </el-select>
        </div>

        <div class="toolbar-actions">
          <input ref="importInput" type="file" accept="application/json,.json" hidden @change="handleImport" />
          <el-tooltip :content="$t('terminology.importJson')">
            <el-button :icon="Upload" circle :aria-label="$t('terminology.importJson')" @click="importInput?.click()" />
          </el-tooltip>
          <el-tooltip :content="$t('terminology.exportJson')">
            <el-button :icon="Download" circle :aria-label="$t('terminology.exportJson')" @click="exportTerms" />
          </el-tooltip>
          <el-button type="primary" :icon="Plus" @click="openCreate">
            {{ $t('terminology.addTerm') }}
          </el-button>
        </div>
      </div>

      <div class="result-line">
        <span>{{ $t('terminology.resultCount', { count: filteredTerms.length }) }}</span>
        <span v-if="hasActiveFilters" class="filter-state">{{ $t('terminology.filtered') }}</span>
      </div>

      <div class="desktop-table">
        <el-table :data="filteredTerms" height="100%" row-key="id">
          <el-table-column :label="$t('terminology.termPair')" min-width="210">
            <template #default="{ row }">
              <div class="term-pair">
                <strong>{{ row.termCn }}</strong>
                <span>{{ row.termEn }}</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="$t('terminology.category')" width="100">
            <template #default="{ row }">
              <span class="category-label">{{ categoryLabel(row.category) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('terminology.definition')" min-width="220" show-overflow-tooltip>
            <template #default="{ row }">
              <span class="definition-text">{{ displayDefinition(row) }}</span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('terminology.aliases')" min-width="140">
            <template #default="{ row }">
              <div class="alias-list">
                <span v-for="alias in displayAliases(row).slice(0, 2)" :key="alias" class="alias-chip">{{ alias }}</span>
                <span v-if="displayAliases(row).length > 2" class="alias-more">+{{ displayAliases(row).length - 2 }}</span>
                <span v-if="displayAliases(row).length === 0" class="muted">-</span>
              </div>
            </template>
          </el-table-column>
          <el-table-column :label="$t('terminology.status')" width="80">
            <template #default="{ row }">
              <span class="status-dot" :class="{ enabled: row.enabled }">
                {{ row.enabled ? $t('terminology.enabled') : $t('terminology.disabled') }}
              </span>
            </template>
          </el-table-column>
          <el-table-column :label="$t('terminology.updatedAt')" width="102" prop="updatedAt" />
          <el-table-column :label="$t('terminology.actions')" width="84" fixed="right">
            <template #default="{ row }">
              <div class="row-actions">
                <el-tooltip :content="$t('terminology.edit')">
                  <el-button text circle :icon="EditPen" :aria-label="$t('terminology.edit')" @click="openEdit(row)" />
                </el-tooltip>
                <el-tooltip :content="$t('terminology.delete')">
                  <el-button text circle type="danger" :icon="Delete" :aria-label="$t('terminology.delete')" @click="removeTerm(row)" />
                </el-tooltip>
              </div>
            </template>
          </el-table-column>
          <template #empty>
            <el-empty :description="$t('terminology.empty')" :image-size="72" />
          </template>
        </el-table>
      </div>

      <div class="mobile-list">
        <article v-for="term in filteredTerms" :key="term.id" class="mobile-term">
          <div class="mobile-term-head">
            <div class="term-pair">
              <strong>{{ term.termCn }}</strong>
              <span>{{ term.termEn }}</span>
            </div>
            <span class="status-dot" :class="{ enabled: term.enabled }">
              {{ term.enabled ? $t('terminology.enabled') : $t('terminology.disabled') }}
            </span>
          </div>
          <p class="mobile-definition">{{ displayDefinition(term) }}</p>
          <div class="mobile-meta">
            <span class="category-label">{{ categoryLabel(term.category) }}</span>
            <span>{{ term.updatedAt }}</span>
            <div class="mobile-actions">
              <el-button text circle :icon="EditPen" :aria-label="$t('terminology.edit')" @click="openEdit(term)" />
              <el-button text circle type="danger" :icon="Delete" :aria-label="$t('terminology.delete')" @click="removeTerm(term)" />
            </div>
          </div>
        </article>
        <el-empty v-if="filteredTerms.length === 0" :description="$t('terminology.empty')" :image-size="72" />
      </div>
    </section>

    <el-dialog
      v-model="dialogVisible"
      :title="editingId === null ? $t('terminology.createTitle') : $t('terminology.editTitle')"
      width="min(640px, 92vw)"
      destroy-on-close
    >
      <el-form label-position="top" class="term-form">
        <div class="form-grid">
          <el-form-item :label="$t('terminology.termCn')" required>
            <el-input v-model="form.termCn" :placeholder="$t('terminology.termCnPlaceholder')" />
          </el-form-item>
          <el-form-item :label="$t('terminology.termEn')" required>
            <el-input v-model="form.termEn" :placeholder="$t('terminology.termEnPlaceholder')" />
          </el-form-item>
        </div>
        <el-form-item :label="$t('terminology.category')" required>
          <el-select v-model="form.category" :placeholder="$t('terminology.categoryPlaceholder')" style="width: 100%">
            <el-option
              v-for="option in categoryOptions.filter(option => option.value)"
              :key="option.value"
              :label="option.label"
              :value="option.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item :label="$t('terminology.definition')">
          <el-input v-model="form.definition" type="textarea" :rows="3" :placeholder="$t('terminology.definitionPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('terminology.aliases')">
          <el-input v-model="form.aliases" :placeholder="$t('terminology.aliasesPlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('terminology.usageNote')">
          <el-input v-model="form.usageNote" type="textarea" :rows="2" :placeholder="$t('terminology.usageNotePlaceholder')" />
        </el-form-item>
        <el-form-item :label="$t('terminology.status')">
          <el-switch
            v-model="form.enabled"
            :active-text="$t('terminology.enabled')"
            :inactive-text="$t('terminology.disabled')"
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">{{ $t('terminology.cancel') }}</el-button>
        <el-button type="primary" :disabled="!canSave" @click="saveTerm">
          {{ $t('terminology.save') }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  CircleCheck,
  Delete,
  Download,
  EditPen,
  Grid,
  Plus,
  Search,
  Tickets,
  Upload
} from '@element-plus/icons-vue'

type TermCategory = 'automotive' | 'position' | 'skill' | 'general'

interface TermItem {
  id: number
  termCn: string
  termEn: string
  category: TermCategory
  definition: string
  definitionEn?: string
  aliases: string[]
  aliasesEn?: string[]
  usageNote: string
  usageNoteEn?: string
  enabled: boolean
  updatedAt: string
}

interface TermForm {
  termCn: string
  termEn: string
  category: TermCategory | ''
  definition: string
  aliases: string
  usageNote: string
  enabled: boolean
}

const { t, locale } = useI18n()
const keyword = ref('')
const categoryFilter = ref('')
const statusFilter = ref('')
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const importInput = ref<HTMLInputElement | null>(null)

const terms = ref<TermItem[]>([
  { id: 1, termCn: '高级驾驶辅助系统', termEn: 'Advanced Driver Assistance Systems (ADAS)', category: 'automotive', definition: '辅助驾驶相关感知、决策与控制功能的总称。', definitionEn: 'A collective term for perception, decision-making, and control functions used in assisted driving.', aliases: ['ADAS', '驾驶辅助系统'], aliasesEn: ['ADAS', 'Driver Assistance System'], usageNote: '首次出现使用全称及缩写。', usageNoteEn: 'Use the full name followed by the abbreviation on first mention.', enabled: true, updatedAt: '2026-08-21' },
  { id: 2, termCn: '电子控制单元', termEn: 'Electronic Control Unit (ECU)', category: 'automotive', definition: '车辆中执行特定控制功能的嵌入式控制器。', definitionEn: 'An embedded controller that performs a specific control function in a vehicle.', aliases: ['ECU', '控制器'], aliasesEn: ['ECU', 'Control Unit'], usageNote: '避免翻译为 electronic controller。', usageNoteEn: 'Avoid the translation “electronic controller.”', enabled: true, updatedAt: '2026-08-20' },
  { id: 3, termCn: '汽车开放系统架构', termEn: 'AUTomotive Open System ARchitecture (AUTOSAR)', category: 'automotive', definition: '汽车软件架构、接口与方法论标准。', definitionEn: 'A standard for automotive software architecture, interfaces, and methodology.', aliases: ['AUTOSAR', 'Autosar'], aliasesEn: ['AUTOSAR', 'Autosar'], usageNote: '品牌缩写统一写作 AUTOSAR。', usageNoteEn: 'Always write the brand abbreviation as AUTOSAR.', enabled: true, updatedAt: '2026-08-20' },
  { id: 4, termCn: '系统工程师', termEn: 'System Engineer', category: 'position', definition: '负责系统需求、架构、集成和验证的工程岗位。', definitionEn: 'An engineering role responsible for system requirements, architecture, integration, and verification.', aliases: ['Systems Engineer'], aliasesEn: ['Systems Engineer'], usageNote: '岗位名称优先使用单数 System Engineer。', usageNoteEn: 'Prefer the singular title “System Engineer.”', enabled: true, updatedAt: '2026-08-19' },
  { id: 5, termCn: '量产项目', termEn: 'Production Program', category: 'general', definition: '已进入产品化开发及交付阶段的客户项目。', definitionEn: 'A customer program that has entered product development and delivery.', aliases: ['SOP Project', 'Mass Production Project'], aliasesEn: ['SOP Project', 'Mass Production Project'], usageNote: '根据上下文区分 program 与 project。', usageNoteEn: 'Choose “program” or “project” according to context.', enabled: true, updatedAt: '2026-08-18' },
  { id: 6, termCn: '需求管理', termEn: 'Requirements Management', category: 'skill', definition: '需求捕获、分析、跟踪、变更与验证的全过程管理。', definitionEn: 'End-to-end management of requirements capture, analysis, traceability, change, and verification.', aliases: ['RM'], aliasesEn: ['RM'], usageNote: '', usageNoteEn: '', enabled: true, updatedAt: '2026-08-18' },
  { id: 7, termCn: '标定', termEn: 'Calibration', category: 'skill', definition: '通过参数调整使控制系统达到目标性能。', definitionEn: 'Adjusting parameters so a control system achieves its target performance.', aliases: ['参数标定'], aliasesEn: ['Parameter Calibration'], usageNote: '车辆控制语境使用 calibration。', usageNoteEn: 'Use “calibration” in vehicle-control contexts.', enabled: true, updatedAt: '2026-08-17' },
  { id: 8, termCn: '软件在环测试', termEn: 'Software-in-the-Loop Testing (SIL)', category: 'skill', definition: '在仿真环境中对软件模型或代码进行闭环测试。', definitionEn: 'Closed-loop testing of software models or code in a simulated environment.', aliases: ['SIL', 'SiL'], aliasesEn: ['SIL', 'SiL'], usageNote: '统一缩写为 SIL。', usageNoteEn: 'Standardize the abbreviation as SIL.', enabled: false, updatedAt: '2026-08-15' }
])

const displayDefinition = (term: TermItem) => locale.value === 'en' ? (term.definitionEn || term.definition) : term.definition
const displayAliases = (term: TermItem) => locale.value === 'en' ? (term.aliasesEn || term.aliases) : term.aliases

const createEmptyForm = (): TermForm => ({
  termCn: '',
  termEn: '',
  category: '',
  definition: '',
  aliases: '',
  usageNote: '',
  enabled: true
})

const form = reactive<TermForm>(createEmptyForm())

const categoryOptions = computed(() => [
  { value: '', label: t('terminology.allCategories') },
  { value: 'automotive', label: t('terminology.categoryAutomotive') },
  { value: 'position', label: t('terminology.categoryPosition') },
  { value: 'skill', label: t('terminology.categorySkill') },
  { value: 'general', label: t('terminology.categoryGeneral') }
])

const statusOptions = computed(() => [
  { value: '', label: t('terminology.allStatuses') },
  { value: 'enabled', label: t('terminology.enabled') },
  { value: 'disabled', label: t('terminology.disabled') }
])

const filteredTerms = computed(() => {
  const query = keyword.value.trim().toLowerCase()
  return terms.value.filter(term => {
    const matchesKeyword = !query || [
      term.termCn,
      term.termEn,
      term.definition,
      ...term.aliases
    ].some(value => value.toLowerCase().includes(query))
    const matchesCategory = !categoryFilter.value || term.category === categoryFilter.value
    const matchesStatus = !statusFilter.value
      || (statusFilter.value === 'enabled' ? term.enabled : !term.enabled)
    return matchesKeyword && matchesCategory && matchesStatus
  })
})

const metrics = computed(() => [
  { label: t('terminology.totalTerms'), value: terms.value.length, icon: Tickets, tone: 'purple' },
  { label: t('terminology.enabledTerms'), value: terms.value.filter(term => term.enabled).length, icon: CircleCheck, tone: 'teal' },
  { label: t('terminology.categoryCount'), value: new Set(terms.value.map(term => term.category)).size, icon: Grid, tone: 'amber' }
])

const hasActiveFilters = computed(() => Boolean(keyword.value || categoryFilter.value || statusFilter.value))
const canSave = computed(() => Boolean(form.termCn.trim() && form.termEn.trim() && form.category))

function categoryLabel(category: TermCategory): string {
  return categoryOptions.value.find(option => option.value === category)?.label || category
}

function openCreate() {
  editingId.value = null
  Object.assign(form, createEmptyForm())
  dialogVisible.value = true
}

function openEdit(term: TermItem) {
  editingId.value = term.id
  Object.assign(form, {
    termCn: term.termCn,
    termEn: term.termEn,
    category: term.category,
    definition: term.definition,
    aliases: term.aliases.join(', '),
    usageNote: term.usageNote,
    enabled: term.enabled
  })
  dialogVisible.value = true
}

function saveTerm() {
  if (!canSave.value) return
  const aliases = form.aliases.split(/[,，]/).map(value => value.trim()).filter(Boolean)
  const payload = {
    termCn: form.termCn.trim(),
    termEn: form.termEn.trim(),
    category: form.category as TermCategory,
    definition: form.definition.trim(),
    aliases,
    usageNote: form.usageNote.trim(),
    enabled: form.enabled,
    updatedAt: '2026-08-21'
  }

  if (editingId.value === null) {
    const nextId = Math.max(0, ...terms.value.map(term => term.id)) + 1
    terms.value.unshift({ id: nextId, ...payload })
    ElMessage.success(t('terminology.createSuccess'))
  } else {
    const index = terms.value.findIndex(term => term.id === editingId.value)
    if (index >= 0) terms.value[index] = { id: editingId.value, ...payload }
    ElMessage.success(t('terminology.updateSuccess'))
  }
  dialogVisible.value = false
}

async function removeTerm(term: TermItem) {
  try {
    await ElMessageBox.confirm(
      t('terminology.deleteConfirm', { term: term.termCn }),
      t('terminology.deleteTitle'),
      { type: 'warning', confirmButtonText: t('terminology.delete'), cancelButtonText: t('terminology.cancel') }
    )
    terms.value = terms.value.filter(item => item.id !== term.id)
    ElMessage.success(t('terminology.deleteSuccess'))
  } catch {
    // Cancellation leaves the local list unchanged.
  }
}

function exportTerms() {
  const blob = new Blob([JSON.stringify(filteredTerms.value, null, 2)], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'terminology-library.json'
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success(t('terminology.exportSuccess'))
}

async function handleImport(event: Event) {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  try {
    const parsed = JSON.parse(await file.text())
    if (!Array.isArray(parsed)) throw new Error('Invalid terminology JSON')
    const imported = parsed
      .filter(item => item && item.termCn && item.termEn)
      .map((item, index): TermItem => ({
        id: Date.now() + index,
        termCn: String(item.termCn).trim(),
        termEn: String(item.termEn).trim(),
        category: ['automotive', 'position', 'skill', 'general'].includes(item.category)
          ? item.category
          : 'general',
        definition: String(item.definition || '').trim(),
        aliases: Array.isArray(item.aliases) ? item.aliases.map(String) : [],
        usageNote: String(item.usageNote || '').trim(),
        enabled: item.enabled !== false,
        updatedAt: '2026-08-21'
      }))
    if (imported.length === 0) throw new Error('No valid terms')
    terms.value.unshift(...imported)
    ElMessage.success(t('terminology.importSuccess', { count: imported.length }))
  } catch {
    ElMessage.error(t('terminology.importFailed'))
  } finally {
    input.value = ''
  }
}
</script>

<style scoped>
.terminology-page {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.metric-strip {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 8px;
  flex-shrink: 0;
}

.metric-item {
  min-width: 0;
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 14px;
  background: #fff;
  border: 1px solid #E8ECF3;
  border-radius: 8px;
}

.metric-icon {
  width: 34px;
  height: 34px;
  flex: 0 0 34px;
  display: grid;
  place-items: center;
  border-radius: 7px;
  font-size: 17px;
}

.metric-icon.purple { background: var(--app-primary-soft); color: var(--app-primary); }
.metric-icon.teal { background: #E8F7F3; color: #178A74; }
.metric-icon.amber { background: #FFF5E6; color: #B56B13; }

.metric-value {
  margin: 0;
  color: #1E1E2D;
  font-size: 18px;
  line-height: 1.1;
  font-weight: 700;
}

.metric-label {
  margin: 3px 0 0;
  color: #8C8CA1;
  font-size: 11px;
}

.terms-workspace {
  min-height: 0;
  flex: 1;
  display: flex;
  flex-direction: column;
  padding: 12px;
  background: #fff;
  border: 1px solid #E8ECF3;
  border-radius: 8px;
  overflow: hidden;
}

.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  flex-shrink: 0;
}

.filter-row,
.toolbar-actions,
.row-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.search-input { width: min(360px, 32vw); }
.filter-select { width: 138px; }
.status-select { width: 112px; }

.result-line {
  min-height: 30px;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #8C8CA1;
  font-size: 11px;
  border-bottom: 1px solid #EEF0F5;
  flex-shrink: 0;
}

.filter-state {
  color: var(--app-primary);
}

.desktop-table {
  flex: 1;
  min-height: 0;
}

.desktop-table :deep(.el-table) {
  --el-table-border-color: #EEF0F5;
  --el-table-header-bg-color: #F8F9FC;
  --el-table-row-hover-bg-color: var(--app-primary-surface);
  font-size: 12px;
}

.desktop-table :deep(.el-table th.el-table__cell) {
  color: #5A5A7A;
  font-weight: 600;
}

.term-pair {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.term-pair strong {
  color: #1E1E2D;
  font-size: 12px;
  line-height: 1.35;
}

.term-pair span,
.definition-text {
  color: #76768F;
  font-size: 11px;
  line-height: 1.45;
}

.category-label,
.alias-chip {
  display: inline-flex;
  align-items: center;
  min-height: 22px;
  padding: 2px 7px;
  border-radius: 4px;
  background: var(--app-primary-soft);
  color: var(--app-primary-dark);
  font-size: 10px;
}

.alias-list {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 4px;
}

.alias-chip {
  background: #F4F5F8;
  color: #666680;
}

.alias-more,
.muted {
  color: #9CA3C4;
  font-size: 10px;
}

.status-dot {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  color: #8C8CA1;
  font-size: 10px;
  white-space: nowrap;
}

.status-dot::before {
  content: '';
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #B7BBC7;
}

.status-dot.enabled { color: #178A74; }
.status-dot.enabled::before { background: #20A886; }

.row-actions { gap: 0; }
.mobile-list { display: none; }

.form-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 12px;
}

.term-form :deep(.el-form-item) {
  margin-bottom: 14px;
}

@media (max-width: 900px) {
  .toolbar {
    align-items: flex-start;
  }

  .filter-row {
    flex-wrap: wrap;
  }

  .search-input { width: 100%; }
}

@media (max-width: 760px) {
  .terminology-page {
    height: auto;
    min-height: 100%;
  }

  .metric-strip {
    grid-template-columns: repeat(3, minmax(0, 1fr));
  }

  .metric-item {
    align-items: flex-start;
    gap: 6px;
    padding: 8px;
  }

  .metric-icon {
    width: 28px;
    height: 28px;
    flex-basis: 28px;
    font-size: 14px;
  }

  .metric-value { font-size: 15px; }
  .metric-label { font-size: 9px; }

  .terms-workspace {
    overflow: visible;
  }

  .toolbar {
    flex-direction: column;
  }

  .filter-row,
  .toolbar-actions {
    width: 100%;
  }

  .filter-select {
    flex: 1;
    width: auto;
  }

  .toolbar-actions {
    justify-content: flex-end;
  }

  .desktop-table { display: none; }
  .mobile-list { display: block; }

  .mobile-term {
    padding: 12px 2px;
    border-bottom: 1px solid #EEF0F5;
  }

  .mobile-term-head,
  .mobile-meta {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 10px;
  }

  .mobile-definition {
    margin: 8px 0;
    color: #666680;
    font-size: 11px;
    line-height: 1.55;
  }

  .mobile-meta {
    justify-content: flex-start;
    color: #9CA3C4;
    font-size: 10px;
  }

  .mobile-actions {
    display: flex;
    margin-left: auto;
  }

  .form-grid {
    grid-template-columns: minmax(0, 1fr);
    gap: 0;
  }
}
</style>
