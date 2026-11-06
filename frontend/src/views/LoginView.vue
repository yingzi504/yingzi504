<template>
  <main class="login-shell">
    <section class="brand-panel" aria-label="HR 文档工作台">
      <div class="brand"><span class="brand-mark">HR</span><span>AI Resume Converter</span></div>
      <div class="brand-copy"><p class="eyebrow">人才文档工作台</p><h1>专注人才，<br>让文档更有条理。</h1><p>在统一的工作空间内处理 CV 与 JD，<br>管理生成文件，查看每一次处理记录。</p></div>
      <div class="document-label"><span>CV</span><i></i><span>JD</span><small>文档处理 · 规范输出 · 记录可查</small></div>
    </section>
    <section class="form-panel">
      <form class="login-card" @submit.prevent="submit">
        <span class="card-mark">HR</span>
        <p class="eyebrow">{{ changing ? '账号安全' : '欢迎使用' }}</p>
        <h2>{{ changing ? '设置你的新密码' : '登录工作台' }}</h2>
        <p class="intro">{{ changing ? (account?.must_change_password ? '首次登录需要修改初始密码，新密码至少 8 位。' : '输入当前密码，并设置至少 8 位的新密码。') : '输入账号名称和密码登录。' }}</p>
        <template v-if="!changing">
          <label for="company-email">账号</label>
          <el-input id="company-email" v-model="email" type="text" placeholder="请输入账号名称（也可填写公司邮箱）" autocomplete="username" size="large" maxlength="254" required />
          <label for="login-password">密码</label>
          <el-input id="login-password" v-model="password" type="password" placeholder="请输入密码" autocomplete="current-password" show-password size="large" maxlength="256" required />
          <p class="help">初始密码为 123456。新账号首次登录时自动创建。</p>
        </template>
        <template v-else>
          <div class="signed-email">{{ account?.email }}</div>
          <label for="current-password">当前密码</label>
          <el-input id="current-password" v-model="password" type="password" autocomplete="current-password" show-password size="large" maxlength="256" required />
          <label for="new-password">新密码</label>
          <el-input id="new-password" v-model="newPassword" type="password" autocomplete="new-password" show-password size="large" minlength="8" maxlength="256" required />
          <label for="confirm-password">确认新密码</label>
          <el-input id="confirm-password" v-model="confirmation" type="password" autocomplete="new-password" show-password size="large" minlength="8" maxlength="256" required />
        </template>
        <p v-if="error" class="form-error" role="alert">{{ error }}</p>
        <el-button class="submit" type="primary" native-type="submit" size="large" :loading="busy">{{ changing ? '保存密码并进入' : '登录' }}</el-button>
        <el-button v-if="changing" class="back" text @click="signOut">退出登录</el-button>
        <p class="footnote">账号无法登录时，请联系管理员。</p>
      </form>
    </section>
  </main>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import http from '@/api/http'
import { account, signOut } from '@/stores/auth'
const route = useRoute(), router = useRouter()
const email = ref(''), password = ref(''), newPassword = ref(''), confirmation = ref('')
const error = ref(''), busy = ref(false)
const changing = computed(() => route.path === '/change-password' || !!account.value?.must_change_password)
async function submit() {
  error.value = ''
  if (changing.value && newPassword.value !== confirmation.value) { error.value = '两次输入的新密码不一致'; return }
  busy.value = true
  try {
    const result: any = changing.value
      ? await http.post('/auth/password', { current_password: password.value, new_password: newPassword.value }, { skipErrorMessage: true })
      : await http.post('/auth/login', { email: email.value, password: password.value }, { skipErrorMessage: true })
    account.value = result.data
    if (account.value?.must_change_password) await router.replace('/change-password')
    else { password.value = ''; newPassword.value = ''; confirmation.value = ''; await router.replace('/upload') }
  } catch (e: any) { error.value = typeof e.response?.data?.detail === 'string' ? e.response.data.detail : '登录或保存失败，请检查输入后重试。' }
  finally { busy.value = false }
}
</script>

<style scoped>
.login-shell{min-height:100dvh;display:grid;grid-template-columns:minmax(300px, 44%) 1fr;background:#f0f2f5;color:#242436;font-family:Inter,'Microsoft YaHei',sans-serif}
.brand-panel{background:#1e1e2d;color:white;padding:40px clamp(24px,5vw,76px);display:flex;flex-direction:column;justify-content:space-between;gap:36px}
.brand{display:flex;align-items:center;gap:12px;font-size:14px;font-weight:600}.brand-mark,.card-mark{display:inline-flex;align-items:center;justify-content:center;background:var(--app-primary);color:white;border-radius:8px;width:40px;height:40px;font-weight:700}
.brand-copy h1{font-size:clamp(28px,3vw,44px);line-height:1.45;font-weight:600;letter-spacing:.02em;margin:20px 0}.brand-copy>p:last-child{font-size:14px;line-height:1.9;color:#bdbdce}.eyebrow{font-size:12px;letter-spacing:.12em;color:var(--app-primary-light-3);margin:0 0 10px}
.document-label{display:flex;align-items:center;gap:14px;flex-wrap:wrap;border-top:1px solid #3a3a52;padding-top:22px}.document-label>span{font-size:22px;font-weight:600}.document-label i{height:22px;width:1px;background:var(--app-primary-dark)}.document-label small{width:100%;color:#aaa9be;font-size:12px}
.form-panel{display:flex;align-items:center;justify-content:center;padding:28px}.login-card{width:100%;max-width:420px;background:white;padding:32px;border:1px solid #e8e8ee;border-radius:12px;box-shadow:0 8px 30px #23233608}.card-mark{display:none}.login-card h2{font-size:26px;margin:0 0 10px;font-weight:600}.intro,.help,.footnote{font-size:12px;color:#858597;line-height:1.7}.intro{margin-bottom:24px}.login-card label{display:block;font-size:13px;margin:17px 0 8px;font-weight:500}.submit{width:100%;margin-top:22px;background:var(--app-primary);border-color:var(--app-primary)}.footnote{margin:18px 0 0;text-align:center}.signed-email{font-size:13px;color:var(--app-primary-dark);overflow-wrap:anywhere}.form-error{font-size:13px;color:#c43636;line-height:1.6}.back{width:100%;margin:8px 0 0}
@media(max-width:760px){.login-shell{grid-template-columns:1fr}.brand-panel{display:none}.form-panel{padding:20px}.card-mark{display:flex;margin-bottom:24px}.login-card{padding:26px}}
@media(max-height:650px) and (min-width:761px){.brand-panel{padding-top:24px;padding-bottom:24px}.login-card{padding:22px 30px}.intro{margin-bottom:12px}.login-card label{margin-top:10px}.form-panel{padding:16px}.submit{margin-top:16px}}
</style>
