<template>
  <section class="admin-page">
    <div class="stats"><div v-for="item in statisticItems" :key="item.key"><span>{{ item.label }}</span><strong>{{ stats[item.key] ?? '—' }}</strong></div></div>
    <div class="admin-card">
      <el-tabs v-model="tab" class="admin-tabs" @tab-change="refresh">
        <el-tab-pane label="用户管理" name="users">
          <div class="toolbar"><el-input v-model="search" placeholder="搜索账号" clearable style="width:260px" @keyup.enter="searchUsers"/><el-button @click="searchUsers">查询</el-button><el-button type="primary" @click="openCreate">创建账号</el-button></div>
          <el-table :data="users" v-loading="busy" height="100%" empty-text="暂无账号">
            <el-table-column prop="id" label="ID" width="65"/><el-table-column prop="email" label="账号" min-width="210" show-overflow-tooltip/>
            <el-table-column label="身份 / 账号类型" min-width="150"><template #default="{row}">{{ row.role==='superadmin'?'超级管理员':row.role==='admin'?'管理员':'用户' }} / {{ row.account_type }}</template></el-table-column>
            <el-table-column label="状态" width="100"><template #default="{row}"><el-tag :type="row.active?'success':'info'">{{ row.active?'启用':'停用' }}</el-tag></template></el-table-column>
            <el-table-column prop="task_count" label="任务数" width="80"/><el-table-column prop="operation_count" label="操作数" width="80"/>
            <el-table-column label="最近登录" width="175"><template #default="{row}">{{ time(row.last_login_at) }}</template></el-table-column>
            <el-table-column label="操作" min-width="260"><template #default="{row}"><div class="row-actions"><el-button v-if="isSuperadmin && row.role==='member'" link type="warning" @click="grantAdmin(row)">授权管理员</el-button><el-button v-if="isSuperadmin && row.role==='admin'" link type="warning" @click="revokeAdmin(row)">收回管理员</el-button><el-button v-if="canManageAccount(row)" link type="primary" @click="openEdit(row)">权限设置</el-button><el-button v-if="canManageAccount(row)" link @click="resetPassword(row)">重置密码</el-button><el-button link @click="viewLogs(row.id)">记录</el-button></div></template></el-table-column>
          </el-table>
          <el-pagination v-model:current-page="userPage" :total="userTotal" :page-size="20" layout="prev,pager,next" @current-change="loadUsers"/>
        </el-tab-pane>
        <el-tab-pane label="操作日志" name="audit">
          <AccountAudit ref="auditPanel" admin :user-id="auditUser" />
        </el-tab-pane>
        <el-tab-pane label="任务与文件" name="files"><AccountRecords admin /></el-tab-pane>
      </el-tabs>
    </div>
    <el-dialog v-model="dialog" :title="editing?'账号与功能权限':'创建账号'" width="min(500px,92vw)">
      <el-form label-position="top" @submit.prevent="saveUser">
        <el-form-item label="账号"><el-input v-model="form.email" type="text" :disabled="!!editing" placeholder="账号名称或公司邮箱"/></el-form-item>
        <el-form-item v-if="!editing" label="身份"><el-radio-group v-model="form.role"><el-radio value="member">普通用户</el-radio><el-radio v-if="isSuperadmin" value="admin">管理员</el-radio></el-radio-group></el-form-item>
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
import AccountAudit from '@/components/AccountAudit.vue'
import http from '@/api/http'
import { account } from '@/stores/auth'
const features=[{key:'cv',label:'CV 处理'},{key:'jd',label:'JD 处理'},{key:'library',label:'JD 库'},{key:'templates',label:'模板管理'},{key:'terminology',label:'术语库'}]
const statisticItems=[{key:'users',label:'账号总数'},{key:'active_users',label:'启用账号'},{key:'logged_in_users',label:'当前登录'},{key:'tasks',label:'处理任务'},{key:'operations',label:'操作记录'}]
const stats=ref<Record<string,number>>({}),tab=ref('users'),users=ref<any[]>([]),busy=ref(false)
const isSuperadmin=account.value?.role==='superadmin'
const search=ref(''),userPage=ref(1),userTotal=ref(0),auditUser=ref(''),auditPanel=ref<InstanceType<typeof AccountAudit>|null>(null)
const dialog=ref(false),editing=ref<number|null>(null),saving=ref(false)
const form=reactive({email:'',role:'member',account_type:'standard',active:true,permissions:features.map(i=>i.key)})
function canManageAccount(row:any){return row.role==='member'||(isSuperadmin&&row.role==='admin')}
function time(value:string|null){return value?new Date(value+'Z').toLocaleString():'未登录'}
async function loadUsers(){busy.value=true;try{const res:any=await http.get('/admin/users',{params:{page:userPage.value,search:search.value}});users.value=res.data;userTotal.value=res.total}catch{}finally{busy.value=false}}
function searchUsers(){userPage.value=1;void loadUsers()}
async function refresh(){try{const res:any=await http.get('/admin/statistics');stats.value=res.data}catch{}if(tab.value==='users')await loadUsers();if(tab.value==='audit')auditPanel.value?.reload()}
function openCreate(){editing.value=null;Object.assign(form,{email:'',role:'member',account_type:'standard',active:true,permissions:features.map(i=>i.key)});dialog.value=true}
function openEdit(row:any){editing.value=row.id;Object.assign(form,{email:row.email,role:row.role,account_type:row.account_type,active:row.active,permissions:[...row.permissions]});dialog.value=true}
async function saveUser(){if(!form.email||!form.account_type.trim()){ElMessage.error('请填写账号和账号类型');return}saving.value=true;try{if(editing.value)await http.put(`/admin/users/${editing.value}`,{active:form.active,account_type:form.account_type,permissions:form.permissions});else await http.post('/admin/users',{email:form.email,role:form.role,account_type:form.account_type,permissions:form.permissions});dialog.value=false;ElMessage.success('账号已保存');await refresh()}catch{}finally{saving.value=false}}
async function resetPassword(row:any){try{await ElMessageBox.confirm(`将 ${row.email} 的密码重置为 123456，并退出其所有登录会话？`,'重置密码',{type:'warning',confirmButtonText:'重置',cancelButtonText:'取消'});await http.post(`/admin/users/${row.id}/reset-password`);ElMessage.success('密码已重置，首次登录需修改')}catch{}}
async function grantAdmin(row:any){try{await ElMessageBox.confirm(`将 ${row.email} 授权为管理员？其当前登录会话会退出，并需重新登录。`,'授权管理员',{type:'warning',confirmButtonText:'授权',cancelButtonText:'取消'});await http.post(`/superadmin/users/${row.id}/grant-admin`);ElMessage.success('管理员授权已完成');await loadUsers()}catch{}}
async function revokeAdmin(row:any){try{await ElMessageBox.confirm(`收回 ${row.email} 的管理员权限？其当前登录会话会退出。`,'收回管理员',{type:'warning',confirmButtonText:'收回',cancelButtonText:'取消'});await http.post(`/superadmin/users/${row.id}/revoke-admin`);ElMessage.success('管理员权限已收回');await loadUsers()}catch{}}
function viewLogs(id:number){auditUser.value=String(id);tab.value='audit'}
onMounted(refresh)
</script>
<style scoped>
.admin-page{height:100%;min-height:0;display:flex;flex-direction:column;gap:16px;overflow:auto}.stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}.stats>div{background:white;border:1px solid #e8e8ee;border-radius:9px;padding:14px 18px;display:flex;flex-direction:column;gap:6px}.stats span{font-size:12px;color:#858597}.stats strong{font-size:26px;color:#343044;font-weight:600}.admin-card{flex:1;min-height:340px;background:white;border:1px solid #e8e8ee;border-radius:10px;padding:16px 20px;overflow:hidden}.admin-tabs{height:100%;display:flex;flex-direction:column}.admin-tabs :deep(.el-tabs__content){flex:1;min-height:0;overflow:auto}.admin-tabs :deep(.el-tab-pane){height:100%;display:flex;flex-direction:column;gap:16px}.admin-tabs :deep(.el-tab-pane[style*="display: none"]){display:none!important}.toolbar{display:flex;gap:10px;flex-wrap:wrap}.el-table{flex:1;min-height:180px}.el-pagination{flex-shrink:0}.row-actions{display:flex;flex-wrap:wrap;gap:8px}.row-actions .el-button{margin:0}.muted{font-size:12px;color:#909399;line-height:1.7}.el-checkbox-group{display:flex;flex-wrap:wrap;gap:4px 14px}.el-checkbox{margin:0}@media(max-width:760px){.stats{grid-template-columns:repeat(2,1fr)}.stats>div{padding:10px}.stats strong{font-size:22px}.admin-card{padding:12px;min-height:420px}}
</style>
