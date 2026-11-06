# AI简历模板转换工具 - 前端实施计划

## 概述

本计划基于 design-document.md 和 tech-stack.md，将项目分为多个小而具体的步骤。每一步都包含明确的验证测试，确保质量。

---

## 阶段一：项目基础架构搭建

### 步骤1.1：后端项目初始化（前端计划中简要记录依赖关系）

**目标：** 确认后端项目结构已创建（由后端计划负责实施）

**说明：** 此步骤主要由后端实施计划负责，前端需要确认后端API已就绪以便后续集成

**验证测试：**
- 确认后端项目目录存在且结构完整

---

### 步骤1.2：前端项目初始化

**目标：** 创建完整的Vue3前端项目结构

**具体指令：**
1. 在 d:\ai_resume\frontend\ 目录下使用Vite创建Vue3+TypeScript项目
2. 配置项目使用pnpm作为包管理器
3. 安装 tech-stack.md 中列出的所有前端依赖
4. 创建完整的目录结构：src/views/、src/stores/、src/api/、src/types/、src/components/、src/utils/
5. 配置 Element Plus 完整引入
6. 配置 Vue Router 和 Pinia
7. 创建 .env.development 和 .env.production 环境变量文件

**验证测试：**
- 确认可以使用 pnpm install 安装所有依赖
- 确认可以使用 pnpm dev 启动开发服务器
- 确认访问 http://localhost:5173 可以看到默认页面
- 确认目录结构完整：src/views/、src/stores/、src/api/、src/types/、src/components/、src/utils/ 都存在
- 确认 Element Plus 组件可以正常导入和使用

---

### 步骤1.3：数据库配置与基础模型（前端计划中简要记录依赖关系）

**目标：** 确认数据库配置已完成（由后端计划负责实施）

**说明：** 此步骤主要由后端实施计划负责

---

## 阶段二：后端API开发（前端计划中简要记录依赖关系）

**说明：** 此阶段主要由后端实施计划负责，前端主要使用后端提供的API

---

## 阶段三：前端UI开发

### 步骤3.1：基础布局与主题配置

**目标：** 创建整体布局框架并配置紫色主题

**具体指令：**
1. 在 src/styles/ 中创建主题样式文件
2. 配置 Element Plus 主题色为 #7C5CFC（紫色）
3. 配置其他配色：背景色 #F0F2F5、卡片背景 #FFFFFF、侧边栏背景 #1E1E2D
4. 创建全局样式（圆角按钮、卡片阴影等）
5. 创建主布局组件（src/layouts/MainLayout.vue）：
   - 左侧导航菜单（6个菜单项）
   - 顶部导航栏（问候语、通知、用户头像）
   - 主内容区
6. 配置 Vue Router 6个路由
7. 采用组件优先思维，将可重用部分提取为独立组件
8. 实现移动优先的响应式设计
9. 设置性能预算目标：页面加载时间<3秒
10. 使用Vue3组合式API（Composition API）
11. 确保完整的TypeScript类型安全

**验证测试：**
- 启动前端，确认页面背景色和主题色正确
- 点击不同导航菜单项，确认路由切换正常
- 验证左侧导航样式（深灰背景、紫色选中状态）
- 检查顶部导航栏显示正确
- 确认响应式布局在不同屏幕尺寸下正常
- 测试移动端适配，确保在小屏幕上显示良好
- 验证页面加载速度<3秒
- 运行TypeScript编译，确认无类型错误

---

### 步骤3.2-3.7：前端各页面开发（通用规范）

**目标：** 实现6个前端页面，符合原型设计和编码规范

**所有前端页面的共同要求（适用于3.2到3.7）：**

1. **界面样式：** 严格符合原型图设计（紫色主题#7C5CFC）
2. **组件优先：** 将可复用UI片段提取为独立组件（src/components/）
3. **TypeScript：** 带完整的类型定义
4. **组合式API：** 使用Vue3 Composition API（`<script setup>`）
5. **Props和Events：** 组件支持Props传参和自定义事件Emit
6. **API封装：** 在 src/api/ 中创建完整的Axios请求函数封装（带错误捕获）
7. **类型定义：** 在 src/types/ 中定义所有请求和返回数据的Interface
8. **Pinia Store：** 每个模块对应的 src/stores/ Store，用于缓存接口数据
9. **响应式设计：** 移动优先，确保多屏幕适配
10. **性能预算：** 页面加载<3秒

**具体补充（步骤3.2-3.7）：**
- 步骤3.2：CV模板库页面 - 同上，增加以上规范要求
- 步骤3.3：JD库页面 - 同上，增加以上规范要求
- 步骤3.4：上传配置页面 - 同上，增加以上规范要求
- 步骤3.5：处理进度页面 - 同上，增加以上规范要求
- 步骤3.6：结果预览页面 - 同上，增加以上规范要求
- 步骤3.7：历史记录页面 - 同上，增加以上规范要求

**验证测试补充（各页面通用）：**
- 确认界面样式与原型图一致
- 验证TypeScript类型完整，编译无错误
- 确认使用Composition API
- 验证API封装完整，带错误处理
- 验证Pinia Store正确缓存数据
- 测试响应式布局在不同屏幕正常
- 验证页面加载速度<3秒
- 每完成2个页面，考虑更新 memory-bank/@architecture.md

---

### 步骤3.2：CV模板库页面

**目标：** 实现模板库管理界面

**具体指令：**
1. 创建 src/views/TemplateLibrary.vue 页面
2. 实现模板分类筛选（纵向/横向）
3. 实现模板列表展示（卡片式，显示预览图）
4. 实现上传新模板功能
5. 实现模板编辑功能
6. 实现模板删除功能
7. 在 src/stores/template.ts 中创建Pinia store
8. 在 src/api/template.ts 中创建API调用函数

**验证测试：**
- 访问模板库页面，确认列表正确显示
- 上传新模板，确认保存成功
- 编辑模板信息，确认更新生效
- 删除模板，确认移除成功
- 测试分类筛选，按分类过滤正确
- 查看模板详情，确认信息完整

---

### 步骤3.3：JD库页面

**目标：** 实现JD管理界面

**具体指令：**
1. 创建 src/views/JDLibrary.vue 页面
2. 实现JD分类筛选（侧边栏分类树）
3. 实现JD列表展示（卡片式，显示使用次数）
4. 实现创建新JD功能（富文本编辑器）
5. 实现JD编辑功能
6. 实现JD删除功能
7. 实现热门JD标记（星形图标）
8. 在 src/stores/jd.ts 中创建Pinia store
9. 在 src/api/jd.ts 中创建API调用函数

**验证测试：**
- 访问JD库页面，确认列表正确显示
- 创建新JD，确认保存成功
- 编辑JD内容，确认更新生效
- 删除JD，确认移除成功
- 测试分类筛选，按分类过滤正确
- 验证使用次数和最后使用时间正确显示
- 标记热门JD，确认星形图标显示

---

### 步骤3.4：上传配置页面

**目标：** 实现任务提交界面

**具体指令：**
1. 创建 src/views/UploadConfig.vue 页面
2. 实现文件上传区域（拖拽上传 + 点击上传）
3. 实现模板选择（下拉选择，显示预览）
4. 实现目标语言选择（中文/英文切换）
5. 实现岗位名称输入
6. 实现JD输入方式选择（从JD库选择 / 手动输入）
7. 实现JD库选择弹窗
8. 实现"开始处理"按钮
9. 在 src/stores/processing.ts 中创建Pinia store
10. 在 src/api/processing.ts 中创建API调用函数

**验证测试：**
- 上传简历文件，确认文件信息正确显示
- 选择不同模板，确认模板预览更新
- 切换语言选项，确认状态更新
- 选择从JD库选择，确认弹窗正常打开
- 选择JD后，确认表单正确填充
- 点击开始处理，确认任务成功提交并跳转

---

### 步骤3.5：处理进度页面

**目标：** 实现Pipeline进度展示界面

**具体指令：**
1. 创建 src/views/ProcessingProgress.vue 页面
2. 实现6步Pipeline的可视化展示（垂直时间线）
3. 每个步骤显示：状态图标、步骤名称、描述、耗时
4. 实现总体进度条（紫色填充）
5. 显示已用时间
6. 实现状态自动刷新（轮询API）
7. 处理完成后自动跳转到结果预览页面
8. 处理失败时显示错误信息和重试按钮

**验证测试：**
- 提交处理任务，跳转到进度页面
- 观察进度从步骤1到步骤6依次完成
- 验证每个步骤的状态正确更新
- 确认进度条百分比正确
- 处理完成后自动跳转
- 模拟错误场景，确认错误信息显示和重试功能

---

### 步骤3.6：结果预览与编辑页面

**目标：** 实现生成结果的预览和编辑

**具体指令：**
1. 创建 src/views/ResultPreview.vue 页面
2. 实现PPT预览区域（使用PPT预览组件或图片轮播）
3. 实现JD匹配度展示（圆形进度条 + 分析报告）
4. 实现结构化数据编辑表单（可编辑Resume各字段）
5. 实现"重新生成PPT"按钮（应用编辑后的数据）
6. 实现下载功能（下载生成的PPT）
7. 实现"返回首页"按钮

**验证测试：**
- 处理完成后跳转到此页面，确认PPT预览正常
- 查看匹配度分析，确认数据正确
- 编辑简历数据，保存后重新生成
- 下载PPT文件，确认文件可正常打开
- 返回首页，确认跳转正确

---

### 步骤3.7：历史记录页面

**目标：** 实现历史记录查看和管理

**具体指令：**
1. 创建 src/views/History.vue 页面
2. 实现顶部统计卡片（总数、成功率、本月处理）
3. 实现筛选栏（日期范围、状态、模板类型）
4. 实现历史记录列表（表格形式）
5. 实现分页功能
6. 实现操作列（下载、查看详情、删除）
7. 实现查看详情弹窗
8. 在 src/stores/history.ts 中创建Pinia store
9. 在 src/api/history.ts 中创建API调用函数

**验证测试：**
- 访问历史页面，确认统计数据正确
- 查看历史列表，确认数据显示正确
- 测试筛选功能（按日期、状态）
- 测试分页功能
- 下载历史PPT，确认文件可访问
- 查看详情弹窗，确认信息完整
- 删除历史记录，确认移除成功

---

### 步骤3.8：TypeScript类型定义完善

**目标：** 确保所有API和数据都有完整的类型定义

**具体指令：**
1. 在 src/types/index.ts 中完善所有接口定义：
   - Resume、ResumeEducation、ResumeExperience、ResumeProject、ResumeSkill
   - Template、TemplateCategory
   - JD、JDCategory
   - ProcessingTask、PipelineStep、ProcessingStatus
   - HistoryRecord、HistoryFilter
   - JDMatch、MatchAnalysis
   - ApiResponse、ApiListResponse
2. 确保所有API函数都使用正确的类型
3. 确保所有Store的state和actions都有类型

**验证测试：**
- 运行TypeScript编译，确认没有类型错误
- 检查API调用，确认请求和响应类型正确
- 检查Store使用，确认类型安全
- 验证组件props和emits都有正确类型

---

## 阶段四：前后端联调与集成测试

> ⚠️ **重要**：此阶段是前后端协作的关键里程碑。完成后前后端可独立修改各自的业务逻辑，但需遵守 **API 契约** 和 **环境配置规范**。后端同步文档见 `implementation-plan-backend.md` 阶段四。

---

### 步骤4.0：联调前置条件 — 环境变量与代理配置

**目标：** 建立前后端独立可切换的环境配置体系，确保开发/生产模式互不干扰。

#### 4.0.1 创建前端环境变量文件

**具体指令：**
1. 创建 `frontend/.env.development`：
```env
# 开发环境 — 使用 Vite 代理转发，避免跨域问题
VITE_API_BASE_URL=/api/v1
VITE_USE_PROXY=true
```
2. 创建 `frontend/.env.production`：
```env
# 生产环境 — 直连后端（Nginx 反向代理或同域部署）
VITE_API_BASE_URL=/api/v1
VITE_USE_PROXY=false
```

> 💡 **独立修改保护**：前端只需改 `.env.*` 即可切换代理/直连模式，无需改动业务代码。后端修改 API 前缀时，前端也只需改一处环境变量。

#### 4.0.2 修改 request.ts 从环境变量读取 baseURL

**当前状态**：✅ 已完成。`baseURL: import.meta.env.VITE_API_BASE_URL || '/api/v1'`

**验证测试：**
- `pnpm dev` 启动后，浏览器 Network 面板确认 API 请求发往 `/api/v1/...`（经 Vite 代理到 `localhost:8000`）
- `pnpm build && pnpm preview` 确认生产模式下 API 请求路径正确

#### 4.0.3 验证 Vite 代理配置

**当前配置**（`vite.config.ts`）：
```ts
server: {
  host: '0.0.0.0',
  port: 3000,
  proxy: {
    '/api': {
      target: 'http://localhost:8000',
      changeOrigin: true
    }
  }
}
```

**验证测试：**
- 前端 `pnpm dev` 启动在 `localhost:3000`
- 浏览器访问 `http://localhost:3000`，F12 Network 确认：
  - `/api/v1/health` 请求发到 `localhost:3000`（被代理到 `localhost:8000`）
  - 响应状态 200
- **不是**直接发到 `localhost:8000`（那是旁路代理的错误行为）

---

### 步骤4.1：API 契约锁定 — 路径与格式对齐

**目标：** 确保前端调用路径与后端路由完全一致，消除双重前缀、路径不匹配等问题。

#### 4.1.1 后端路由规范速查

| 模块 | 路由前缀 | 完整示例 |
|------|----------|----------|
| 根路由 | `/api/v1` | `app.include_router(api_router, prefix="/api/v1")` |
| 健康检查 | `/health` | `GET /health` |
| 简历处理 | `/api/v1/resume` | `POST /api/v1/resume/upload` |
| 任务编排 | `/api/v1/process` | `POST /api/v1/process` |
| 模板管理 | `/api/v1/template` | `GET /api/v1/template/list` |
| JD 管理 | `/api/v1/jd` | `GET /api/v1/jd/list` |
| 历史记录 | `/api/v1/history` | `GET /api/v1/history/list` |
| 术语表 | `/api/v1/termbase` | `GET /api/v1/termbase` |

#### 4.1.2 前端 API 路径验证（✅ 当前已正确）

**当前 `src/api/index.ts` 路径状态**：所有路径以 `/resume/`、`/process/`、`/template/` 等开头，与 `baseURL=/api/v1` 拼接后完整匹配后端路由。

**验证清单**：

| API 函数 | 代码路径 | 实际请求 | 后端路由 |
|----------|----------|----------|----------|
| `resumeApi.upload` | `/resume/upload` | `/api/v1/resume/upload` | ✅ |
| `resumeApi.process` | `/process` | `/api/v1/process` | ✅ |
| `resumeApi.getProcessStatus` | `/process/{id}` | `/api/v1/process/{id}` | ✅ |
| `resumeApi.downloadPPTX` | `/resume/fill/download/{name}?format=pptx` | `/api/v1/resume/fill/download/{name}?format=pptx` | ✅ |
| `templateApi.list` | `/template/list` | `/api/v1/template/list` | ✅ |
| `jdApi.list` | `/jd/list` | `/api/v1/jd/list` | ✅ |
| `historyApi.list` | `/history/list` | `/api/v1/history/list` | ✅ |
| `termbaseApi.get` | `/termbase` | `/api/v1/termbase` | ✅ |

#### 4.1.3 请求/响应格式契约

**前端 TypeScript 接口**（与后端 `ApiResponse` 对齐）：
```ts
// src/types/index.ts — 所有 API 统一使用
interface ApiResponse<T = any> {
  success: boolean
  data: T
  message: string
  timestamp: string
}

interface ApiListResponse<T = any> {
  success: boolean
  data: {
    items: T[]
    total: number
    page: number
    pageSize: number
  }
  message: string
  timestamp: string
}
```

**后端错误格式**（与 design-document.md §10.1 对齐）：
```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "message": "请求参数验证失败",
  "details": { ... },
  "timestamp": "2026-07-06T10:30:00Z"
}
```

> 💡 **独立修改保护**：后端修改字段时必须同步更新 Swagger 文档（前端以此为准）；前端修改类型定义时必须与后端 Swagger 文档对齐。

---

### 步骤4.2：文件上传联调

**目标：** 验证前端上传→后端接收→返回文件ID 的完整链路。

**前端实现要求：**
1. 使用 `FormData` 包装文件，**不要手动设置 `Content-Type`**（让浏览器自动生成含 `boundary` 的 `multipart/form-data`）
2. Pinia store（`stores/upload.ts`）管理上传状态（loading、progress、error）
3. 上传成功后保存 `file_id` 以供后续 Pipeline 提交

**联调验证项：**
- PDF 文件上传成功，返回 `file_id`
- Word 文件上传成功
- 超过 10MB 时返回错误，前端展示 ElMessage 提示
- 不支持的类型返回错误

> 💡 **独立修改保护**：文件大小上限在 `backend/.env` 的 `MAX_UPLOAD_SIZE_MB` 中配置；前端上传进度 UI 可独立调整，不影响后端。

**验证测试：**
- 上传 PDF（<10MB），确认收到 `{"success":true, "data":{"file_id":"xxx"}}`
- 上传 >10MB 文件，确认显示"文件大小超出限制"
- 上传 .exe，确认显示"不支持的文件类型"

---

### 步骤4.3：Pipeline 提交与轮询联调

**目标：** 验证提交→异步处理→轮询状态→获取结果 完整链路。

**前端实现要求：**
1. `stores/processing.ts` 管理 Pipeline 状态
2. 轮询间隔 2-3 秒（`setInterval`），任务完成/失败时 `clearInterval`
3. 进度页动态渲染 `steps` 数组（**不硬编码步骤数量**，后端决定步骤数）
4. 每步状态图标：`pending`→⏳ `in_progress`→🔄 `completed`→✅ `failed`→❌

**轮询状态响应格式**（前后端约定）：
```json
{
  "success": true,
  "data": {
    "task_id": "uuid",
    "status": "processing",
    "percentage": 50,
    "steps": [
      {"step": 1, "name": "文档解析", "status": "completed", "duration": "0.4s"},
      {"step": 2, "name": "LLM结构化抽取", "status": "completed", "duration": "38s"},
      {"step": 3, "name": "翻译+脱敏", "status": "in_progress", "duration": null},
      {"step": 4, "name": "约束性摘要", "status": "pending", "duration": null},
      {"step": 5, "name": "PPT模板填充", "status": "pending", "duration": null}
    ]
  }
}
```

> 💡 **独立修改保护**：轮询间隔由前端独立控制；Pipeline 步骤数/顺序由后端独立控制，前端动态渲染不硬编码。

**验证测试：**
- 提交任务 → 跳转进度页 → 轮询开始
- 5 个步骤依次从 `pending` → `in_progress` → `completed`
- 进度条从 0% → 100%
- 完成后自动跳转结果预览页
- 后端中断 → 前端显示 ElMessage 错误，不白屏

---

### 步骤4.4：PPT/PDF 下载联调

**目标：** 验证文件下载链路（blob 处理、中文文件名、双格式支持）。

**前端实现要求：**
1. 下载使用 `responseType: 'blob'`
2. 从 `Content-Disposition` 响应头解析文件名（优先 `filename*=UTF-8''`）
3. `URL.createObjectURL(blob)` + `<a download>` 触发下载
4. 下载完成后 `URL.revokeObjectURL()` 释放内存
5. Pinia store 管理下载状态

**联调验证项：**
- PPTX 下载文件名含中文无乱码（如 `IAV_Mr.Zhang_HUD_Resume_EN.pptx`）
- PDF 下载正常
- 文件可打开且内容完整

> 💡 **独立修改保护**：文件命名规则由后端控制；前端只负责 blob 下载，不构造文件名。

**验证测试：**
- 点击"下载 PPTX" → 文件正确下载且可打开
- 点击"下载 PDF" → PDF 下载成功
- 文件名中文无乱码
- Console 无 blob URL 内存泄漏

---

### 步骤4.5：管理功能 CRUD 联调

**目标：** 验证模板库/JD库/历史记录的前后端 CRUD 连通。

**逐模块验证：**

| 模块 | 操作 | 前端验证点 |
|------|------|-----------|
| 模板库 | 列表/上传/删除 | 列表渲染、上传刷新、删除二次确认 |
| JD库 | 列表/创建/编辑/删除 | 分类筛选、创建回显、编辑保存 |
| 历史记录 | 列表/统计/删除 | 分页、状态筛选、统计卡片数据 |

> 💡 **独立修改保护**：每类资源的接口路径和字段名锁定；后端新增字段遵循"向后兼容"（可选字段）；前端新增展示字段不影响已有功能。

**验证测试：**
- 创建→列表刷新→编辑→列表刷新→删除→列表刷新 全流程走通
- 网络错误时显示 ElMessage 错误提示，不崩溃

---

### 步骤4.6：前端联调完整 Checklist

完成以上所有步骤后，逐项验证：

| # | 检查项 | 方法 |
|---|--------|------|
| 1 | `pnpm dev` 正常启动在 `:3000` | 浏览器访问 |
| 2 | `.env.development` 中 `VITE_API_BASE_URL` 已配置 | 检查文件存在 |
| 3 | `request.ts` 的 `baseURL` 使用环境变量（非硬编码） | 检查代码 |
| 4 | Network 面板 API 请求路径无双重 `/api/v1/` 前缀 | F12 Network |
| 5 | 所有 API 请求经 Vite 代理（Request URL 为 `:3000/api/...`） | F12 Network |
| 6 | 无 CORS 报错 | F12 Console |
| 7 | 文件上传成功 | 首页上传 PDF |
| 8 | Pipeline 进度页步骤动态更新（不硬编码步骤数） | 提交任务观察 |
| 9 | PPT/PDF 下载成功且文件名无乱码 | 下载文件检查 |
| 10 | 模板库 CRUD 正常 | 逐项操作 |
| 11 | JD库 CRUD + 分类筛选正常 | 逐项操作 |
| 12 | 历史记录分页 + 筛选 + 统计正常 | 逐项操作 |
| 13 | 错误处理：断后端后前端不白屏 | 停后端刷新页面 |

---

### 步骤4.7：接口版本化策略（预防）

**策略：**
1. URL 版本化：当前 `/api/v1/`，未来 breaking change 使用 `/api/v2/`
2. 字段向后兼容：新增可选、删除先标记 `@deprecated` 保留一版、重命名新旧并存
3. 前端类型同步：后端 Swagger 更新后，手动更新 `src/types/index.ts`

> 💡 **独立修改保护**：后端新增 `/api/v2/` 不影响前端对 `/api/v1/` 的调用；前端迁移 v2 时只需修改 API 函数路径，UI 组件不变。

---

### 步骤4.8：前端性能优化

**目标：** 首屏加载 < 3 秒。

**具体指令：**
1. Element Plus 按需引入（当前为完整引入，可优化）
2. 路由懒加载（`() => import(...)`）
3. 加载骨架屏（skeleton）用于 Pipeline 进度页
4. 列表分页默认 `pageSize=10`
5. 打包产物分析（`rollup-plugin-visualizer`）

**验证测试：**
- Lighthouse 评分 > 90
- 首屏加载 < 3 秒
- 打包体积 < 500KB（gzip）

---

## 阶段五：文档与部署

### 步骤5.1：完善开发文档

**目标：** 确保文档完整准确

**具体指令：**
1. 更新 frontend/README.md，包含：
   - 环境配置步骤
   - 依赖安装
   - 开发和构建命令
2. 更新项目根目录 README.md，包含：
   - 项目简介
   - 快速开始指南
   - 功能特性
   - 技术栈
   - 目录结构说明

**验证测试：**
- 按照文档步骤，新用户能成功搭建开发环境
- 文档清晰易懂，没有遗漏关键步骤
- 所有命令都能正常执行

---

### 步骤5.2：生产环境配置与部署准备

**目标：** 准备生产部署

**具体指令：**
1. 配置前端生产环境变量
2. 编写前端构建和部署脚本
3. 优化前端构建产物

**验证测试：**
- 前端构建成功，无错误
- 所有功能在生产配置下正常工作

---

## 实施顺序总结

```
阶段一：基础架构
  ↓
步骤1.1 后端初始化（依赖） → 步骤1.2 前端初始化 → 步骤1.3 数据库配置（依赖）
  ↓
阶段二：后端API（依赖）
  ↓
阶段三：前端UI
  ↓
步骤3.1 基础布局 → 步骤3.2 模板库页 → 步骤3.3 JD库页
  ↓
步骤3.4 上传配置页 → 步骤3.5 处理进度页 → 步骤3.6 结果预览页
  ↓
步骤3.7 历史记录页 → 步骤3.8 类型定义完善
  ↓
阶段四：测试优化（依赖）
  ↓
阶段五：文档部署
  ↓
步骤5.1 文档完善 → 步骤5.2 部署准备
```

---

## 关键里程碑

| 里程碑 | 完成标准 |
|--------|----------|
| M1：基础就绪 | 后端和前端都能启动，数据库配置完成 |
| M2：管理功能完成 | 模板库和JD库的前端页面完成 |
| M3：Pipeline完成 | 后端6个处理步骤全部实现（后端里程碑） |
| M4：UI完成 | 所有6个前端页面都完成 |
| M5：集成完成 | 端到端流程能完整跑通 |
| M6：发布就绪 | 文档完善，可部署生产 |

---

## 关键规范补充（基于 .github/copilot-instructions.md）

### 前端开发强制规范
1. **原型一致** - 界面样式必须符合原型图要求
2. **TypeScript全覆盖** - 完整的类型定义，无隐式any
3. **Composition API** - 使用Vue3组合式API
4. **组件化** - 组件优先思维，可复用、可组合的UI片段
5. **Props和Events** - 组件支持Props传参和自定义事件Emit
6. **API封装** - 在 src/api/ 中创建完整的Axios请求函数封装（带错误捕获）
7. **类型定义** - 在 src/types/ 中定义所有请求和返回数据的Interface
8. **Pinia Store** - 每个模块对应的 src/stores/ Store，用于缓存接口数据
9. **响应式设计** - 移动优先
10. **性能预算** - 页面加载时间<3秒

---

## 注意事项

1. **严格按顺序执行** - 每个步骤依赖前序步骤完成
2. **每步必须验证** - 完成一步后立即执行验证测试，确认无误再继续
3. **保持代码质量** - 遵循项目编码规范
4. **及时更新文档** - 如发现设计文档需要更新，及时修改
5. **小步快跑** - 每个步骤都是小目标，便于验证和调整
6. **规范强制执行** - 所有前端规范必须遵守，不能妥协
