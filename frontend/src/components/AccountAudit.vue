<template>
  <div class="audit-records">
    <div class="filters">
      <el-input v-if="admin" v-model="userFilter" placeholder="用户 ID" clearable style="width:120px" />
      <el-select v-model="category" placeholder="全部分类" clearable style="width:160px"><el-option v-for="item in categories" :key="item.value" :label="item.label" :value="item.value" /></el-select>
      <el-select v-model="result" placeholder="全部结果" clearable style="width:130px"><el-option label="成功" value="success" /><el-option label="失败" value="failed" /></el-select>
      <el-input v-model="action" placeholder="操作关键词" clearable style="width:200px" @keyup.enter="reload" />
      <el-button type="primary" @click="reload">查询 / 刷新</el-button>
    </div>
    <div v-if="admin" class="filters">
      <el-input v-model="accountType" placeholder="账号类型" clearable style="width:140px" />
      <el-input v-model="department" placeholder="部门代码" clearable style="width:140px" />
      <el-select v-model="resourceType" placeholder="资源类型" clearable style="width:140px"><el-option v-for="item in resourceTypes" :key="item" :label="item.toUpperCase()" :value="item" /></el-select>
      <el-date-picker v-model="dates" type="datetimerange" start-placeholder="开始时间" end-placeholder="结束时间" style="width:360px;max-width:100%" />
    </div>
    <div class="summary"><span>共 {{ total }} 条</span><el-tag type="success">成功 {{ summary.success }}</el-tag><el-tag type="danger">失败 {{ summary.failed }}</el-tag><el-tag v-for="item in categoryCounts" :key="item.value" type="info">{{ item.label }} {{ item.count }}</el-tag></div>
    <el-table v-loading="busy" :data="rows" height="100%" empty-text="暂无匹配的操作记录">
      <el-table-column label="时间" width="175"><template #default="{row}">{{ formatTime(row.created_at) }}</template></el-table-column>
      <el-table-column v-if="admin" prop="email" label="操作账号" min-width="180"><template #default="{row}">{{ row.email || '未登录 / 系统' }}</template></el-table-column>
      <el-table-column prop="category_label" label="分类" width="125" />
      <el-table-column prop="action" label="操作" min-width="260" show-overflow-tooltip />
      <el-table-column v-if="admin" prop="account_type" label="账号类型" width="110" />
      <el-table-column prop="resource_type" label="资源" width="90" />
      <el-table-column v-if="admin" prop="department" label="部门" width="90" />
      <el-table-column prop="resource_id" label="关联记录" min-width="160" show-overflow-tooltip />
      <el-table-column label="结果" width="100"><template #default="{row}"><el-tag :type="row.result === 'success' ? 'success' : 'danger'">{{ row.result === 'success' ? '成功' : '失败' }} {{ row.status_code }}</el-tag></template></el-table-column>
      <el-table-column v-if="admin" prop="ip_address" label="来源 IP（脱敏）" width="145" />
    </el-table>
    <el-pagination v-model:current-page="page" :total="total" :page-size="30" layout="prev, pager, next" @current-change="load" />
  </div>
</template>
<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import http from '@/api/http'
const props=defineProps<{admin?:boolean;userId?:string}>()
const rows=ref<any[]>([]),total=ref(0),page=ref(1),busy=ref(false),category=ref(''),result=ref(''),action=ref('')
const userFilter=ref(props.userId||''),accountType=ref(''),department=ref(''),resourceType=ref(''),dates=ref<[Date,Date]|null>(null)
const categories=ref<{value:string;label:string}[]>([]),summary=ref<{success:number;failed:number;by_category:Record<string,number>}>({success:0,failed:0,by_category:{}})
const resourceTypes=['cv','jd','upload','file','user','resource','audit','legacy']
const categoryCounts=computed(()=>categories.value.map(item=>({...item,count:summary.value.by_category[item.value]||0})).filter(item=>item.count))
function formatTime(value:string){return new Date(value).toLocaleString()}
async function load(){busy.value=true;try{const res:any=await http.get(props.admin?'/admin/audit':'/audit',{params:{page:page.value,category:category.value||undefined,result:result.value||undefined,action:action.value||undefined,...(props.admin?{user_id:userFilter.value||undefined,account_type:accountType.value||undefined,department:department.value||undefined,resource_type:resourceType.value||undefined,start:dates.value?.[0]?.toISOString(),end:dates.value?.[1]?.toISOString()}:{})}});rows.value=res.data;total.value=res.total;categories.value=res.categories||[];summary.value=res.summary}catch{rows.value=[];total.value=0;summary.value={success:0,failed:0,by_category:{}}}finally{busy.value=false}}
function reload(){page.value=1;void load()}
watch(()=>props.userId,value=>{userFilter.value=value||'';reload()})
defineExpose({reload})
onMounted(load)
</script>
<style scoped>
.audit-records{display:flex;flex-direction:column;gap:14px;min-height:0;height:100%}.filters,.summary{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.summary{font-size:12px;color:#606266}.el-table{flex:1;min-height:200px}.el-pagination{flex-shrink:0}
</style>
