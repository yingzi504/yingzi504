<template>
  <div class="records">
    <div class="filters">
      <el-input v-if="admin" v-model="userFilter" placeholder="用户 ID（可选）" clearable style="width:180px" @keyup.enter="reload" />
      <el-select v-model="status" placeholder="全部状态" clearable style="width:150px" @change="reload"><el-option label="已完成" value="completed"/><el-option label="失败" value="failed"/><el-option label="待补充信息" value="awaiting_input"/><el-option label="处理中" value="processing"/></el-select>
      <el-button @click="reload">刷新</el-button><span class="count">共 {{ total }} 条记录</span>
    </div>
    <el-table v-loading="busy" :data="rows" height="100%" empty-text="暂无处理记录，完成文档处理后可在此调取文件。">
      <el-table-column prop="name" label="原始文件 / 任务" min-width="210" show-overflow-tooltip />
      <el-table-column v-if="admin" prop="email" label="所属账号" min-width="200"><template #default="{row}">{{ row.email || '启用账号系统前的文件' }}</template></el-table-column>
      <el-table-column prop="kind" label="类型" width="85"><template #default="{row}">{{ row.kind === 'legacy' ? '历史文件' : row.kind.toUpperCase() }}</template></el-table-column>
      <el-table-column label="状态" width="110"><template #default="{row}">{{ labels[row.status] || row.status }}</template></el-table-column>
      <el-table-column label="记录时间" width="175"><template #default="{row}">{{ formatTime(row.created_at) }}</template></el-table-column>
      <el-table-column label="文件与详情" min-width="230"><template #default="{row}"><div class="actions"><el-button link type="primary" @click="details(row.id)">详情</el-button><el-button v-for="file in row.files" :key="file.format" link type="primary" :disabled="!file.available || downloading === row.id + file.format" @click="download(row.id,file)">{{ file.format.toUpperCase() }}</el-button></div></template></el-table-column>
    </el-table>
    <el-pagination v-model:current-page="page" :total="total" :page-size="20" layout="prev, pager, next" @current-change="load" />
    <el-dialog v-model="showDetails" title="处理记录" width="min(640px, 92vw)"><template v-if="selected"><el-descriptions :column="1" border><el-descriptions-item label="任务编号">{{ selected.id }}</el-descriptions-item><el-descriptions-item label="文件">{{ selected.name }}</el-descriptions-item><el-descriptions-item label="状态">{{ labels[selected.status] || selected.status }}</el-descriptions-item><el-descriptions-item label="更新时间">{{ formatTime(selected.updated_at) }}</el-descriptions-item></el-descriptions><p v-if="selected.metadata?.current_step">当前步骤：{{ selected.metadata.current_step }}</p><p v-if="selected.metadata?.error_message" role="alert">处理说明：{{ selected.metadata.error_message }}</p></template></el-dialog>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from 'vue'
import http from '@/api/http'
defineProps<{admin?:boolean}>()
const rows=ref<any[]>([]), total=ref(0), page=ref(1), busy=ref(false), status=ref(''), userFilter=ref('')
const showDetails=ref(false), selected=ref<any>(null), downloading=ref('')
const labels:Record<string,string>={pending:'排队中',processing:'处理中',awaiting_input:'待补充信息',completed:'已完成',failed:'失败',interrupted:'服务重启中断'}
function formatTime(value:string){return new Date(value+'Z').toLocaleString()}
async function load(){busy.value=true;try{const res:any=await http.get('/records',{params:{page:page.value,status:status.value || undefined,user_id:userFilter.value || undefined}});rows.value=res.data;total.value=res.total}catch{}finally{busy.value=false}}
function reload(){page.value=1;void load()}
async function details(id:string){try{const res:any=await http.get(`/records/${id}`);selected.value=res.data;showDetails.value=true}catch{}}
async function download(id:string,file:any){downloading.value=id+file.format;try{const blob:Blob=await http.get(`/records/${id}/download`,{params:{format:file.format},responseType:'blob'});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=file.name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000)}catch{}finally{downloading.value=''}}
onMounted(load)
</script>
<style scoped>
.records{display:flex;flex-direction:column;gap:16px;min-height:0;height:100%}.filters{display:flex;gap:10px;align-items:center;flex-wrap:wrap}.count{font-size:12px;color:#909399}.actions{display:flex;gap:8px;flex-wrap:wrap}.actions .el-button{margin:0}.el-table{flex:1;min-height:200px}.el-pagination{flex-shrink:0}pre{white-space:pre-wrap;overflow-wrap:anywhere;max-height:35vh;overflow:auto;font-size:12px;color:#666}
</style>
