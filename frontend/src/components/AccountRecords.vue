<template>
  <div class="records">
    <div class="filters">
      <el-input v-if="admin" v-model="userFilter" :placeholder="t('records.userIdOptional')" clearable style="width:180px" @keyup.enter="reload" />
      <el-select v-model="status" :placeholder="t('records.allStatuses')" clearable style="width:150px" @change="reload"><el-option :label="t('records.completed')" value="completed"/><el-option :label="t('records.failed')" value="failed"/><el-option :label="t('records.awaiting')" value="awaiting_input"/><el-option :label="t('records.processing')" value="processing"/></el-select>
      <el-select v-model="kind" :placeholder="t('records.allTypes')" clearable style="width:130px" @change="reload"><el-option label="CV" value="cv"/><el-option label="JD" value="jd"/><el-option v-if="admin" :label="t('records.legacy')" value="legacy"/></el-select>
      <el-input v-model="department" :placeholder="t('records.departmentCode')" clearable style="width:140px" @keyup.enter="reload" />
      <el-button @click="reload">{{ t('records.refresh') }}</el-button><span class="count">{{ t('records.total',{count:total}) }}</span>
    </div>
    <el-table v-loading="busy" :data="rows" height="100%" :empty-text="t('records.empty')">
      <el-table-column prop="name" :label="t('records.originalFile')" min-width="210" show-overflow-tooltip />
      <el-table-column v-if="admin" prop="email" :label="t('records.owner')" min-width="200"><template #default="{row}">{{ row.email || t('records.preAccountFile') }}</template></el-table-column>
      <el-table-column prop="kind" :label="t('records.type')" width="85"><template #default="{row}">{{ row.kind === 'legacy' ? t('records.legacy') : row.kind.toUpperCase() }}</template></el-table-column>
      <el-table-column :label="t('records.status')" width="110"><template #default="{row}">{{ statusLabel(row.status) }}</template></el-table-column>
      <el-table-column :label="t('records.recordedAt')" width="175"><template #default="{row}">{{ formatTime(row.created_at) }}</template></el-table-column>
      <el-table-column :label="t('records.filesAndDetails')" min-width="230"><template #default="{row}"><div class="actions"><el-button link type="primary" @click="details(row.id)">{{ t('records.details') }}</el-button><el-button v-for="file in row.files" :key="file.format" link type="primary" :disabled="!file.available || downloading === row.id + file.format" @click="download(row.id,file)">{{ file.format.toUpperCase() }}</el-button></div></template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :total="total" :page-size="20" layout="prev, pager, next" @current-change="load" />
    <el-dialog v-model="showDetails" :title="t('records.dialogTitle')" width="min(640px, 92vw)"><template v-if="selected"><el-descriptions :column="1" border><el-descriptions-item :label="t('records.taskId')">{{ selected.id }}</el-descriptions-item><el-descriptions-item :label="t('records.file')">{{ selected.name }}</el-descriptions-item><el-descriptions-item :label="t('records.status')">{{ statusLabel(selected.status) }}</el-descriptions-item><el-descriptions-item :label="t('records.updatedAt')">{{ formatTime(selected.updated_at) }}</el-descriptions-item></el-descriptions><p v-if="selected.metadata?.current_step">{{ t('records.currentStep',{step:selected.metadata.current_step}) }}</p><p v-if="selected.metadata?.error_message" role="alert">{{ t('records.processingNote',{message:selected.metadata.error_message}) }}</p></template></el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '@/api/http'
const {t,locale}=useI18n()
defineProps<{admin?:boolean}>()
const rows=ref<any[]>([]), total=ref(0), page=ref(1), busy=ref(false), status=ref(''), userFilter=ref(''), kind=ref(''), department=ref('')
const showDetails=ref(false), selected=ref<any>(null), downloading=ref('')
const statusKeys:Record<string,string>={pending:'pending',processing:'processing',awaiting_input:'awaiting',completed:'completed',failed:'failed',interrupted:'interrupted'}
function statusLabel(status:string){return statusKeys[status]?t(`records.${statusKeys[status]}`):status}
function formatTime(value:string){return new Date(value+'Z').toLocaleString(locale.value)}
async function load(){busy.value=true;try{const res:any=await http.get('/records',{params:{page:page.value,status:status.value||undefined,user_id:userFilter.value||undefined,kind:kind.value||undefined,department:department.value||undefined}});rows.value=res.data;total.value=res.total}catch{}finally{busy.value=false}}
function reload(){page.value=1;void load()}
async function details(id:string){try{const res:any=await http.get(`/records/${id}`);selected.value=res.data;showDetails.value=true}catch{}}
async function download(id:string,file:any){downloading.value=id+file.format;try{const blob:Blob=await http.get(`/records/${id}/download`,{params:{format:file.format},responseType:'blob'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=file.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch{}finally{downloading.value=''}}
onMounted(load)
</script>
<style scoped>
.records{display:flex;flex-direction:column;gap:16px;min-height:0;height:100%}.filters{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.count{font-size:12px;color:#909399}.actions{display:flex;gap:8px;flex-wrap:wrap}.actions .el-button{margin:0}.el-table{flex:1;min-height:200px}.el-pagination{flex-shrink:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:35vh;overflow:auto;font-size:12px;color:#666}
</style>
