<template>
  <section class="admin-page">
    <div class="stats"><div v-for="item in statisticItems" :key="item.key"><span>{{ item.label }}</span><strong>{{ stats[item.key] ?? '—' }}</strong></div></div>
    <div class="admin-card">
      <el-tabs v-model="tab" class="admin-tabs" @tab-change="refresh">
        <el-tab-pane :label="t('admin.users')" name="users">
          <div class="toolbar"><el-input v-model="search" :placeholder="t('admin.searchAccount')" clearable style="width:260px" @keyup.enter="searchUsers"/><el-button @click="searchUsers">{{t('admin.search')}}</el-button><el-button type="primary" @click="openCreate">{{t('admin.createAccount')}}</el-button></div>
          <el-table :data="users" v-loading="busy" height="100%" :empty-text="t('admin.noAccounts')">
            <el-table-column prop="id" label="ID" width="65"/><el-table-column prop="email" :label="t('admin.account')" min-width="210" show-overflow-tooltip/>
            <el-table-column :label="t('admin.identityType')" min-width="150"><template #default="{row}">{{ roleLabel(row.role) }} / {{ row.account_type }}</template></el-table-column>
            <el-table-column :label="t('admin.status')" width="100"><template #default="{row}"><el-tag :type="row.active?'success':'info'">{{ row.active?t('admin.enabled'):t('admin.disabled') }}</el-tag></template></el-table-column>
            <el-table-column prop="task_count" :label="t('admin.tasks')" width="80"/><el-table-column prop="operation_count" :label="t('admin.operations')" width="80"/>
            <el-table-column :label="t('admin.lastLogin')" width="175"><template #default="{row}">{{ time(row.last_login_at) }}</template></el-table-column>
            <el-table-column :label="t('admin.actions')" min-width="260"><template #default="{row}"><div class="row-actions"><el-button v-if="isSuperadmin && row.role==='member'" link type="warning" @click="grantAdmin(row)">{{t('admin.grantAdmin')}}</el-button><el-button v-if="isSuperadmin && row.role==='admin'" link type="warning" @click="revokeAdmin(row)">{{t('admin.revokeAdmin')}}</el-button><el-button v-if="canManageAccount(row)" link type="primary" @click="openEdit(row)">{{t('admin.permissions')}}</el-button><el-button v-if="canManageAccount(row)" link @click="resetPassword(row)">{{t('admin.resetPassword')}}</el-button><el-button link @click="viewLogs(row.id)">{{t('admin.records')}}</el-button></div></template></el-table-column>
          </el-table>
          <el-pagination v-model:current-page="userPage" :total="userTotal" :page-size="20" layout="prev,pager,next" @current-change="loadUsers"/>
        </el-tab-pane>
        <el-tab-pane :label="t('admin.audit')" name="audit">
          <AccountAudit ref="auditPanel" admin :user-id="auditUser" />
        </el-tab-pane>
        <el-tab-pane :label="t('admin.files')" name="files"><AccountRecords admin /></el-tab-pane>
      </el-tabs>
    </div>
    <el-dialog v-model="dialog" :title="editing?t('admin.editDialog'):t('admin.createDialog')" width="min(500px,92vw)">
      <el-form label-position="top" @submit.prevent="saveUser">
        <el-form-item :label="t('admin.account')"><el-input v-model="form.email" type="text" :disabled="!!editing" :placeholder="t('admin.accountPlaceholder')"/></el-form-item>
        <el-form-item v-if="!editing" :label="t('admin.identity')"><el-radio-group v-model="form.role"><el-radio value="member">{{t('admin.regularUser')}}</el-radio><el-radio v-if="isSuperadmin" value="admin">{{t('admin.administrator')}}</el-radio></el-radio-group></el-form-item>
        <el-form-item :label="t('admin.accountType')"><el-input v-model="form.account_type" :placeholder="t('admin.accountTypePlaceholder')" maxlength="50"/></el-form-item>
        <el-form-item :label="t('admin.availableFeatures')"><el-checkbox-group v-model="form.permissions" :disabled="form.role==='admin'"><el-checkbox v-for="item in features" :key="item.key" :value="item.key">{{item.label}}</el-checkbox></el-checkbox-group><span v-if="form.role==='admin'" class="muted">{{t('admin.adminAllFeatures')}}</span></el-form-item>
        <el-form-item v-if="editing" :label="t('admin.accountStatus')"><el-switch v-model="form.active" :disabled="form.role==='admin'" :active-text="t('admin.enabled')" :inactive-text="t('admin.disabled')"/></el-form-item>
        <p v-if="!editing" class="muted">{{t('admin.initialPasswordHelp')}}</p>
      </el-form>
      <template #footer><el-button @click="dialog=false">{{t('admin.cancel')}}</el-button><el-button type="primary" :loading="saving" @click="saveUser">{{t('admin.save')}}</el-button></template>
    </el-dialog>
  </section>
</template>
<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useI18n } from 'vue-i18n'
import { ElMessage, ElMessageBox } from 'element-plus'
import AccountRecords from '@/components/AccountRecords.vue'
import AccountAudit from '@/components/AccountAudit.vue'
import http from '@/api/http'
import { account } from '@/stores/auth'
const {t,locale}=useI18n()
const features=computed(()=>[{key:'cv',label:t('admin.featureCv')},{key:'jd',label:t('admin.featureJd')},{key:'library',label:t('admin.featureLibrary')},{key:'templates',label:t('admin.featureTemplates')},{key:'terminology',label:t('admin.featureTerminology')}])
const statisticItems=computed(()=>[{key:'users',label:t('admin.statUsers')},{key:'active_users',label:t('admin.statActive')},{key:'logged_in_users',label:t('admin.statLoggedIn')},{key:'tasks',label:t('admin.statTasks')},{key:'operations',label:t('admin.statOperations')}])
const stats=ref<Record<string,number>>({}),tab=ref('users'),users=ref<any[]>([]),busy=ref(false)
const isSuperadmin=account.value?.role==='superadmin'
const search=ref(''),userPage=ref(1),userTotal=ref(0),auditUser=ref(''),auditPanel=ref<InstanceType<typeof AccountAudit>|null>(null)
const dialog=ref(false),editing=ref<number|null>(null),saving=ref(false)
const form=reactive({email:'',role:'member',account_type:'standard',active:true,permissions:features.value.map(i=>i.key)})
function canManageAccount(row:any){return row.role==='member'||(isSuperadmin&&row.role==='admin')}
function roleLabel(role:string){return t(`admin.${role==='superadmin'?'superadmin':role==='admin'?'administrator':'member'}`)}
function time(value:string|null){return value?new Date(value+'Z').toLocaleString(locale.value):t('admin.neverSignedIn')}
async function loadUsers(){busy.value=true;try{const res:any=await http.get('/admin/users',{params:{page:userPage.value,search:search.value}});users.value=res.data;userTotal.value=res.total}catch{}finally{busy.value=false}}
function searchUsers(){userPage.value=1;void loadUsers()}
async function refresh(){try{const res:any=await http.get('/admin/statistics');stats.value=res.data}catch{}if(tab.value==='users')await loadUsers();if(tab.value==='audit')auditPanel.value?.reload()}
function openCreate(){editing.value=null;Object.assign(form,{email:'',role:'member',account_type:'standard',active:true,permissions:features.value.map(i=>i.key)});dialog.value=true}
function openEdit(row:any){editing.value=row.id;Object.assign(form,{email:row.email,role:row.role,account_type:row.account_type,active:row.active,permissions:[...row.permissions]});dialog.value=true}
async function saveUser(){if(!form.email||!form.account_type.trim()){ElMessage.error(t('admin.fillRequired'));return}saving.value=true;try{if(editing.value)await http.put(`/admin/users/${editing.value}`,{active:form.active,account_type:form.account_type,permissions:form.permissions});else await http.post('/admin/users',{email:form.email,role:form.role,account_type:form.account_type,permissions:form.permissions});dialog.value=false;ElMessage.success(t('admin.saved'));await refresh()}catch{}finally{saving.value=false}}
async function resetPassword(row:any){try{await ElMessageBox.confirm(t('admin.resetConfirm',{email:row.email}),t('admin.resetPassword'),{type:'warning',confirmButtonText:t('admin.confirmReset'),cancelButtonText:t('admin.cancel')});await http.post(`/admin/users/${row.id}/reset-password`);ElMessage.success(t('admin.resetDone'))}catch{}}
async function grantAdmin(row:any){try{await ElMessageBox.confirm(t('admin.grantConfirm',{email:row.email}),t('admin.grantAdmin'),{type:'warning',confirmButtonText:t('admin.confirmGrant'),cancelButtonText:t('admin.cancel')});await http.post(`/superadmin/users/${row.id}/grant-admin`);ElMessage.success(t('admin.grantDone'));await loadUsers()}catch{}}
async function revokeAdmin(row:any){try{await ElMessageBox.confirm(t('admin.revokeConfirm',{email:row.email}),t('admin.revokeAdmin'),{type:'warning',confirmButtonText:t('admin.confirmRevoke'),cancelButtonText:t('admin.cancel')});await http.post(`/superadmin/users/${row.id}/revoke-admin`);ElMessage.success(t('admin.revokeDone'));await loadUsers()}catch{}}
function viewLogs(id:number){auditUser.value=String(id);tab.value='audit'}
onMounted(refresh)
</script>
<style scoped>
.admin-page{height:100%;min-height:0;display:flex;flex-direction:column;gap:16px;overflow:auto}.stats{display:grid;grid-template-columns:repeat(5,minmax(0,1fr));gap:12px}.stats>div{background:white;border:1px solid #e8e8ee;border-radius:9px;padding:14px 18px;display:flex;flex-direction:column;gap:6px}.stats span{font-size:12px;color:#858597}.stats strong{font-size:26px;color:#343044;font-weight:600}.admin-card{flex:1;min-height:340px;background:white;border:1px solid #e8e8ee;border-radius:10px;padding:16px 20px;overflow:hidden}.admin-tabs{height:100%;display:flex;flex-direction:column}.admin-tabs :deep(.el-tabs__content){flex:1;min-height:0;overflow:auto}.admin-tabs :deep(.el-tab-pane){height:100%;display:flex;flex-direction:column;gap:16px}.admin-tabs :deep(.el-tab-pane[style*="display: none"]){display:none!important}.toolbar{display:flex;gap:10px;flex-wrap:wrap}.el-table{flex:1;min-height:180px}.el-pagination{flex-shrink:0}.row-actions{display:flex;flex-wrap:wrap;gap:8px}.row-actions .el-button{margin:0}.muted{font-size:12px;color:#909399;line-height:1.7}.el-checkbox-group{display:flex;flex-wrap:wrap;gap:4px 14px}.el-checkbox{margin:0}@media(max-width:760px){.stats{grid-template-columns:repeat(2,1fr)}.stats>div{padding:10px}.stats strong{font-size:22px}.admin-card{padding:12px;min-height:420px}}
</style>
