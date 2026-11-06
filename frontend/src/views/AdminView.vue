<template>
  <section class="admin-page">
    <div class="stats"><div v-for="item in statisticItems" :key="item.key"><span>{{ item.label }}</span><strong>{{ stats[item.key] ?? '—' }}</strong></div></div>
    <div class="admin-card">
      <el-tabs v-model="tab" class="admin-tabs" @tab-change="refresh">
        <el-tab-pane label="用户管理" name="users">
          <div class="toolbar"><el-input v-model="search" placeholder="搜索账号" clearable style="width:260px" @keyup.enter="searchUsers"/><el-button @click="searchUsers">查询</el-button><el-button type="primary" @click="openCreate">创建账号</el-button></div>
          <el-table :data="users" v-loading="busy" height="100%" empty-text="暂无账号">
            <el-table-column prop="id" label="ID" width="65"/><el-table-column prop="email" label="账号" min-width="210" show-overflow-tooltip/>
            <el-table-column label="身份 / 账号类型" min-width="150"><template #default="{row}">{{ row.role==='admin'?'管理员':'用户' }} / {{ row.account_type }}</template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="{row}"><el-tag :type="row.active?'success':'info'">{{ row.active?'启用':'停用' }}</el-tag></template></el-table-column>
            <el-table-column prop="task_count" label="任务数" width="80"/><el-table-column prop="operation_count" label="操作数" width="80"/>
            <el-table-column label="最近登录" width="175"><template #default="{row}">{{ time(row.last_login_at) }}</template></el-table-column>
            <el-table-column label="操作" min-width="210"><template #default="{row}"><div class="row-actions"><el-button link type="primary" @click="openEdit(row)">权限设置</el-button><el-button link @click="resetPassword(row)">重置密码</el-button><el-button link @click="viewLogs(row.id)">记录</el-button></div></template></el-table-column>
          </el-table>
          <el-pagination v-model:current-page="userPage" :total="userTotal" :page-size="20" layout="prev,pager,next" @current-change="loadUsers"/>
        </el-tab-pane>
        <el-tab-pane label="操作日志" name="audit">
          <div class="toolbar"><el-input v-model="auditUser" placeholder="用户 ID" clearable style="width:130px"/><el-input v-model="auditAction" placeholder="筛选操作，如 login、download" clearable style="width:270px" @keyup.enter="searchAudit"/><el-button @click="searchAudit">查询 / 刷新</el-button></div>
          <el-table :data="events" v-loading="busy" height="100%" empty-text="暂无匹配的操作记录">
            <el-table-column label="时间" width="175"><template #default="{row}">{{ time(row.created_at) }}</template></el-table-column><el-table-column prop="email" label="用户" min-width="190"><template #default="{row}">{{row.email||'未登录 / 系统'}}</template></el-table-column><el-table-column prop="action" label="操作" min-width="280"/><el-table-column prop="resource_id" label="关联记录" min-width="170" show-overflow-tooltip/><el-table-column label="结果" width="95"><template #default="{row}"><el-tag :type="row.status_code<400?'success':'danger'">{{row.status_code}}</el-tag></template></el-table-column><el-table-column prop="ip_address" label="来源 IP" width="135"/>
          </el-table>
          <el-pagination v-model:current-page="auditPage" :total="auditTotal" :page-size="30" layout="prev,pager,next" @current-change="loadAudit"/>
        </el-tab-pane>
        <el-tab-pane label="任务与文件" name="files"><AccountRecords admin /></el-tab-pane>
      </el-tabs>
    </div>
    <el-dialog v-model="dialog" :title="editing?'账号与功能权限':'创建账号'" width="min(500px,92vw)">
      <el-form label-position="top" @submit.prevent="saveUser">
        <el-form-item label="账号"><el-input v-model="form.email" type="text" :disabled="!!editing" placeholder="账号名称或公司邮箱"/></el-form-item>
        <el-form-item v-if="!editing" label="身份"><el-radio-group v-model="form.role"><el-radio value="member">普通用户</el-radio><el-radio value="admin">管理员</el-radio></el-radio-group></el-form-item>
        <el-form-item label="账号类型"><el-input v-model="form.account_type" placeholder="例如 standard、hr、trial" maxlength="50"/></el-form-item>
        <el-form-item label="可用功能"><el-checkbox-group v-model="form.permissions" :disabled="form.role==='admin'"><el-checkbox v-for="item in features" :key="item.key" :value="item.key">{{item.label}}</el-checkbox></el-checkbox-group><span v-if="form.role==='admin'" class="muted">管理员可使用全部功能。</span></el-form-item>
        <el-form-item v-if="editing" label="账号状态"><el-switch v-model="form.active" :disabled="form.role==='admin'" active-text="启用" inactive-text="停用"/></el-form-item>
        <p v-if="!editing" class="muted">初始密码为 123456，用户首次登录后需修改。</p>
      </el-form>
      <template #footer><el-button @click="dialog=false">取消</el-button><el-button type="primary" :loading="saving" @click="saveUser">保存</el-button></template>
    </el-dialog>
  </section>
</template>
<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import AccountRecords from '@/components/AccountRecords.vue'
import http from '@/api/http'
const features=[{key:'cv',label:'CV 处理'},{key:'jd',label:'JD 处理'},{key:'library',label:'JD 库'},{key:'templates',label:'模板管理'},{key:'terminology',label:'术语库'}]
const statisticItems=[{key:'users',label:'账号总数'},{key:'active_users',label:'启用账号'},{key:'tasks',label:'处理任务'},{key:'completed',label:'完成任务'},{key:'operations',label:'操作记录'}]
const stats=ref<Record<string,number>>({}),tab=ref('users'),users=ref<any[]>([]),events=ref<any[]>([]),busy=ref(false)
const search=ref(''),userPage=ref(1),userTotal=ref(0),auditUser=ref(''),auditAction=ref(''),auditPage=ref(1),auditTotal=ref(0)
const dialog=ref(false),editing=ref<number|null>(null),saving=ref(false)
const form=reactive({email:'',role:'member',account_type:'standard',active:true,permissions:features.map(i=>i.key)})
function time(value:string|null){return value?new Date(value+'Z').toLocaleString():'未登录'}
async function loadUsers(){busy.value=true;try{const res:any=await http.get('/admin/users',{params:{page:userPage.value,search:search.value}});users.value=res.data;userTotal.value=res.total}catch{}finally{busy.value=false}}
async function loadAudit(){busy.value=true;try{const res:any=await http.get('/admin/audit',{params:{page:auditPage.value,user_id:auditUser.value||undefined,action:auditAction.value||undefined}});events.value=res.data;auditTotal.value=res.total}catch{}finally{busy.value=false}}
function searchUsers(){userPage.value=1;void loadUsers()}function searchAudit(){auditPage.value=1;void loadAudit()}
async function refresh(){try{const res:any=await http.get('/admin/statistics');stats.value=res.data}catch{}if(tab.value==='users')await loadUsers();if(tab.value==='audit')await loadAudit()}
function openCreate(){editing.value=null;Object.assign(form,{email:'',role:'member',account_type:'standard',active:true,permissions:features.map(i=>i.key)});dialog.value=true}
function openEdit(row:any){editing.value=row.id;Object.assign(form,{email:row.email,role:row.role,account_type:row.account_type,active:row.active,permissions:[...row.permissions]});dialog.value=true}
async function saveUser(){if(!form.email||!form.account_type.trim()){ElMessage.error('请填写账号和账号类型');return}saving.value=true;try{if(editing.value)await http.put(`/admin/users/${editing.value}`,{active:form.active,account_type:form.account_type,permissions:form.permissions});else await http.post('/admin/users',{email:form.email,role:form.role,account_type:form.account_type,permissions:form.permissions});dialog.value=false;ElMessage.success('账号已保存');await refresh()}catch{}finally{saving.value=false}}
async function resetPassword(row:any){try{await ElMessageBox.confirm(`将 ${row.email} 的密码重置为 123456，并退出其所有登录会话？`,'重置密码',{type:'warning',confirmButtonText:'重置',cancelButtonText:'取消'});await http.post(`/admin/users/${row.id}/reset-password`);ElMessage.success('密码已重置，首次登录需修改')}catch{}}
function viewLogs(id:number){auditUser.value=String(id);auditPage.value=1;tab.value='audit';void loadAudit()}
onMounted(refresh)
</script>
<style scoped>
.admin-page{height:100%;min-height:0;display:flex;flex-direction:column;gap:16px;overflow:auto}.stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}.stats>div{background:white;border:1px solid #e8e8ee;border-radius:9px;padding:14px 18px;display:flex;flex-direction:column;gap:6px}.stats span{font-size:12px;color:#858597}.stats strong{font-size:26px;color:#343044;font-weight:600}.admin-card{flex:1;min-height:340px;background:white;border:1px solid #e8e8ee;border-radius:10px;padding:16px 20px;overflow:hidden}.admin-tabs{height:100%;display:flex;flex-direction:column}.admin-tabs :deep(.el-tabs__content){flex:1;min-height:0;overflow:auto}.admin-tabs :deep(.el-tab-pane){height:100%;display:flex;flex-direction:column;gap:16px}.admin-tabs :deep(.el-tab-pane[style*="display: none"]){display:none!important}.toolbar{display:flex;gap:10px;flex-wrap:wrap}.el-table{flex:1;min-height:180px}.el-pagination{flex-shrink:0}.row-actions{display:flex;flex-wrap:wrap;gap:8px}.row-actions .el-button{margin:0}.muted{font-size:12px;color:#909399;line-height:1.7}.el-checkbox-group{display:flex;flex-wrap:wrap;gap:4px 14px}.el-checkbox{margin:0}@media(max-width:760px){.stats{grid-template-columns:repeat(2,1fr)}.stats>div{padding:10px}.stats strong{font-size:22px}.admin-card{padding:12px;min-height:420px}}
</style>
