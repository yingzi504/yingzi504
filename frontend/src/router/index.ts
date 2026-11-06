
import { createRouter, createWebHistory } from 'vue-router'
import type { RouteRecordRaw } from 'vue-router'
import { refreshAccount, canUse } from '@/stores/auth'

const routes: RouteRecordRaw[] = [
  { path: '/login', component: () => import('@/views/LoginView.vue') },
  { path: '/change-password', component: () => import('@/views/LoginView.vue') },
  {
    path: '/',
    component: () => import('@/layouts/MainLayout.vue'),
    redirect: '/upload',
    children: [
      {
        path: 'cv-library',
        name: 'CVLibrary',
        component: () => import('@/views/CVLibraryView.vue'),
        meta: { title: 'CV Library', description: 'Browse completed CVs by department and target position.' }
      },
      { path: 'recruitment-tools', name: 'RecruitmentTools', component: () => import('@/views/RecruitmentToolsView.vue') },
      { path: 'offboarding-tools', name: 'OffboardingTools', component: () => import('@/views/EmptyModuleView.vue') },
      { path: 'admin', component: () => import('@/views/AdminView.vue'), meta: { title: '管理后台' } },
      {
        path: 'upload',
        name: 'Upload',
        component: () => import('@/views/UploadView.vue'),
        meta: {
          title: 'CV/JD Upload & Processing',
          description: 'Upload a CV or JD, configure processing options, and preview the result in real time.'
        }
      },
      {
        path: 'history',
        name: 'History',
        component: () => import('@/views/RecordsView.vue'),
        meta: {
          title: 'History',
          description: 'Filter and view history records by processing status, output language, content type, and more.'
        }
      },
      {
        path: 'templates',
        name: 'Templates',
        component: () => import('@/views/TemplatesView.vue'),
        meta: {
          title: 'Templates',
          description: 'Manage resume PPT templates and upload new versions.'
        }
      },
      {
        path: 'jd-library',
        name: 'JDLibrary',
        component: () => import('@/views/JDLibraryView.vue'),
        meta: {
          title: 'JD Library',
          description: 'Manage job descriptions, upload and maintain internal JDs, and search by category and language.'
        }
      },
      {
        path: 'terminology',
        name: 'Terminology',
        component: () => import('@/views/TerminologyView.vue'),
        meta: {
          title: 'Terminology Library',
          description: 'Maintain standardized Chinese and English terminology used by CV and JD agents.'
        }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  let user
  try { user = await refreshAccount() }
  catch { return to.path === '/login' ? true : '/login' }
  if (!user) return to.path === '/login' ? true : '/login'
  if (user.must_change_password) return to.path === '/change-password' ? true : '/change-password'
  if (to.path === '/login') return '/upload'
  if (to.path === '/admin' && user.role !== 'admin') return '/upload'
  if (to.path === '/upload' && !canUse('cv') && !canUse('jd')) return '/history'
  const features: Record<string, string> = { '/cv-library': 'cv', '/templates': 'templates', '/jd-library': 'library', '/terminology': 'terminology' }
  const feature = features[to.path]
  if (feature && !canUse(feature)) return '/history'
  return true
})

export default router
