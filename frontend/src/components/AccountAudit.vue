<template>
  <div class="audit-records">
    <div class="filters">
      <el-input v-if="admin" v-model="userFilter" :placeholder="t('audit.userId')" clearable style="width:120px" />
      <el-select v-model="category" :placeholder="t('audit.allCategories')" clearable style="width:160px"><el-option v-for="item in categories" :key="item.value" :label="categoryLabel(item.value)" :value="item.value" /></el-select>
      <el-select v-model="result" :placeholder="t('audit.allResults')" clearable style="width:130px"><el-option :label="t('audit.success')" value="success" /><el-option :label="t('audit.failed')" value="failed" /></el-select>
      <el-input v-model="action" :placeholder="t('audit.actionKeyword')" clearable style="width:200px" @keyup.enter="reload" />
      <el-button type="primary" @click="reload">{{ t('audit.queryRefresh') }}</el-button>
    </div>
    <div v-if="admin" class="filters">
      <el-input v-model="accountType" :placeholder="t('audit.accountType')" clearable style="width:140px" />
      <el-input v-model="department" :placeholder="t('audit.departmentCode')" clearable style="width:140px" />
      <el-select v-model="resourceType" :placeholder="t('audit.resourceType')" clearable style="width:140px"><el-option v-for="item in resourceTypes" :key="item" :label="item.toUpperCase()" :value="item" /></el-select>
      <el-date-picker v-model="dates" type="datetimerange" :start-placeholder="t('audit.startTime')" :end-placeholder="t('audit.endTime')" style="width:360px;max-width:100%" />
    </div>
    <div class="summary"><span>{{ t('audit.total',{count:total}) }}</span><el-tag type="success">{{ t('audit.summarySuccess',{count:summary.success}) }}</el-tag><el-tag type="danger">{{ t('audit.summaryFailed',{count:summary.failed}) }}</el-tag><el-tag v-for="item in categoryCounts" :key="item.value" type="info">{{ categoryLabel(item.value) }} {{ item.count }}</el-tag></div>
    <el-table v-loading="busy" :data="rows" height="100%" :empty-text="t('audit.empty')">
      <el-table-column :label="t('audit.time')" width="175"><template #default="{row}">{{ formatTime(row.created_at) }}</template></el-table-column>
      <el-table-column v-if="admin" prop="email" :label="t('audit.actor')" min-width="180"><template #default="{row}">{{ row.email || t('audit.signedOutSystem') }}</template></el-table-column>
      <el-table-column :label="t('audit.category')" width="125"><template #default="{row}">{{ categoryLabel(row.category) }}</template></el-table-column>
      <el-table-column prop="action" :label="t('audit.action')" min-width="260" show-overflow-tooltip />
      <el-table-column v-if="admin" prop="account_type" :label="t('audit.accountType')" width="110" />
      <el-table-column prop="resource_type" :label="t('audit.resource')" width="90" />
      <el-table-column v-if="admin" prop="department" :label="t('audit.department')" width="90" />
      <el-table-column prop="resource_id" :label="t('audit.relatedRecord')" min-width="160" show-overflow-tooltip />
      <el-table-column :label="t('audit.result')" width="100"><template #default="{row}"><el-tag :type="row.result === 'success' ? 'success' : 'danger'">{{ row.result === 'success' ? t('audit.success') : t('audit.failed') }} {{ row.status_code }}</el-tag></template></el-table-column>
      <el-table-column v-if="admin" prop="ip_address" :label="t('audit.maskedIp')" width="145" />
    </el-table>
    <el-pagination v-model:current-page="page" :total="total" :page-size="30" layout="prev, pager, next" @current-change="load" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'
import http from '@/api/http'
const { t, locale } = useI18n()
const props=defineProps<{admin?:boolean;userId?:string}>()
const rows=ref<any[]>([]),total=ref(0),page=ref(1),busy=ref(false),category=ref(''),result=ref(''),action=ref('')
const userFilter=ref(props.userId||''),accountType=ref(''),department=ref(''),resourceType=ref(''),dates=ref<[Date,Date]|null>(null)
const categories=ref<{value:string;label:string}[]>([]),summary=ref<{success:number;failed:number;by_category:Record<string,number>}>({success:0,failed:0,by_category:{}})
const resourceTypes=['cv','jd','upload','file','user','resource','audit','legacy']
const categoryCounts=computed(()=>categories.value.map(item=>({...item,count:summary.value.by_category[item.value]||0})).filter(item=>item.count))
function categoryLabel(value:string){return t(`audit.categories.${value}`)}
function formatTime(value:string){return new Date(value).toLocaleString(locale.value)}
async function load(){busy.value=true;try{const res:any=await http.get(props.admin?'/admin/audit':'/audit',{params:{page:page.value,category:category.value||undefined,result:result.value||undefined,action:action.value||undefined,...(props.admin?{user_id:userFilter.value||undefined,account_type:accountType.value||undefined,department:department.value||undefined,resource_type:resourceType.value||undefined,start:dates.value?.[0]?.toISOString(),end:dates.value?.[1]?.toISOString()}:{})}});rows.value=res.data;total.value=res.total;categories.value=res.categories||[];summary.value=res.summary}catch{rows.value=[];total.value=0;summary.value={success:0,failed:0,by_category:{}}}finally{busy.value=false}}
function reload(){page.value=1;void load()}
watch(()=>props.userId,value=>{userFilter.value=value||'';reload()})
defineExpose({reload})
onMounted(load)
</script>
<style scoped>
.audit-records{display:flex;flex-direction:column;gap:14px;min-height:0;height:100%}.filters,.summary{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.summary{font-size:12px;color:#606266}.el-table{flex:1;min-height:200px}.el-pagination{flex-shrink:0}
</style>
