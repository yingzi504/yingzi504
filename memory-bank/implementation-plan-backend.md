# AI简历模板转换工具 - 后端实施计划

## 概述

本计划基于 design-document.md 和 tech-stack.md，将项目分为多个小而具体的步骤。每一步都包含明确的验证测试，确保质量。

---

## 阶段一：项目基础架构搭建

### 步骤1.1：后端项目初始化

**前置工作：**
- 在编写任何代码之前，先阅读 memory-bank/@architecture.md 和 memory-bank/@design-document.md（如存在）

**目标：** 创建完整的FastAPI后端目录结构

**具体指令：**
1. 在 d:\ai_resume\backend\ 目录下创建完整的项目结构
2. 确保包含 app/ 主目录，下含 api/（routers）、services/、schemas/、models/、core/ 子目录
3. 创建 requirements.txt 文件，列出所有后端依赖（技术栈：FastAPI, Pydantic, SQLAlchemy）
4. 创建 .env.example 环境变量示例文件
5. 创建 README.md 后端开发文档
6. 配置 conda 环境管理

**验证测试：**
- 确认目录结构完整：app/api/、app/services/、app/schemas/、app/models/、app/core/ 都存在
- 确认 requirements.txt 包含 tech-stack.md 中列出的所有依赖
- 确认可以创建并激活conda环境
- 确认可以成功安装所有依赖（使用 pip install -r requirements.txt）

---

### 步骤1.2：前端项目初始化（后端计划中简要记录依赖关系）

**目标：** 确认前端项目结构已创建（由前端计划负责实施）

**说明：** 此步骤主要由前端实施计划负责，后端需要确认前端项目结构已就绪以便后续集成测试

**验证测试：**
- 确认前端项目目录存在且结构完整

---

### 步骤1.3：数据库配置与基础模型

**目标：** 配置SQLAlchemy并创建核心数据模型

**具体指令：**
1. 在 app/core/config.py 中配置数据库连接（SQLite）
2. 在 app/core/database.py 中配置SQLAlchemy引擎和会话
3. 在 app/models/ 目录下创建基础模型类
4. 创建以下数据模型：
   - Resume（简历数据）
   - ProcessingTask（处理任务）
   - Template（PPT模板）
   - JD（岗位描述）
   - HistoryRecord（历史记录）
5. 在 app/main.py 中添加数据库初始化逻辑

**验证测试：**
- 启动FastAPI应用，确认没有数据库连接错误
- 访问Swagger文档（http://localhost:8000/docs）确认页面正常加载
- 确认可以通过SQLAlchemy创建数据库表
- 确认可以进行基本的数据库CRUD操作（使用测试脚本）

---

## 阶段二：后端API开发

### 步骤2.1：文件上传与存储API

**目标：** 实现简历文件上传和存储功能

**具体指令：**
1. 在 app/schemas/file.py 中创建文件上传相关的Pydantic模型（严格校验请求体、查询参数、响应体）
2. 在 app/services/file_service.py 中实现文件存储服务
3. 在 app/api/v1/files.py 中创建文件上传API端点（路由层）
4. 支持的文件格式：PDF、Word（.doc、.docx）
5. 实现文件大小限制检查（最大10MB）
6. 实现文件类型验证
7. 使用 FastAPI 的 HTTPException 捕获异常，返回标准化的 JSON 错误格式
8. 确保 Swagger UI 文档自动生成且质量良好
9. 在关键代码处添加简要注释

**验证测试：**
- 使用curl或Postman上传PDF文件，确认返回200状态码和文件ID
- 上传超过10MB的文件，确认返回400错误和适当提示
- 上传不支持的文件格式（如图片），确认返回400错误
- 检查上传的文件是否正确保存在指定目录
- 访问Swagger文档（http://localhost:8000/docs）确认API端点正确显示且文档清晰
- 验证所有Pydantic模型正常工作，数据校验生效
- 确认错误返回格式标准化

---

### 步骤2.2：CV模板库管理API

**目标：** 实现PPT模板的上传、列表、下载、删除功能

**具体指令：**
1. 在 app/schemas/template.py 中创建模板相关的Pydantic模型（严格校验）
2. 在 app/models/template.py 中创建Template数据库模型
3. 在 app/services/template_service.py 中实现模板管理服务
4. 在 app/api/v1/templates.py 中创建模板管理API端点（路由层）：
   - POST /api/v1/templates - 上传新模板
   - GET /api/v1/templates - 获取模板列表
   - GET /api/v1/templates/{id} - 获取单个模板详情
   - PUT /api/v1/templates/{id} - 更新模板信息
   - DELETE /api/v1/templates/{id} - 删除模板
   - GET /api/v1/templates/{id}/download - 下载模板文件
5. 实现模板分类（纵向/横向）
6. 实现模板版本管理
7. 使用 HTTPException 处理异常，返回标准化 JSON 错误
8. 确保 Swagger UI 文档完善
9. 关键代码添加注释

**验证测试：**
- 上传PPT模板文件，确认保存成功并返回模板信息
- 获取模板列表，确认返回正确的数据结构
- 更新模板信息（如版本号、分类），确认更新生效
- 删除模板，确认从数据库和文件系统中移除
- 下载模板文件，确认文件完整性
- 测试模板分类筛选功能
- 访问Swagger文档确认所有端点文档完整
- 验证Pydantic校验生效
- 完成此里程碑后，更新 memory-bank/@architecture.md

---

### 步骤2.3：JD库管理API

**目标：** 实现岗位描述的增删改查功能

**具体指令：**
1. 在 app/schemas/jd.py 中创建JD相关的Pydantic模型（严格校验）
2. 在 app/models/jd.py 中创建JD数据库模型
3. 在 app/services/jd_service.py 中实现JD管理服务
4. 在 app/api/v1/jds.py 中创建JD管理API端点（路由层）：
   - POST /api/v1/jds - 创建新JD
   - GET /api/v1/jds - 获取JD列表
   - GET /api/v1/jds/{id} - 获取单个JD详情
   - PUT /api/v1/jds/{id} - 更新JD
   - DELETE /api/v1/jds/{id} - 删除JD
5. 实现JD分类筛选（产品管理、汽车技术、软件等）
6. 实现使用次数统计和最后使用时间更新
7. 使用 HTTPException 处理异常，返回标准化 JSON 错误
8. 确保 Swagger UI 文档完善
9. 关键代码添加注释

**验证测试：**
- 创建新JD，确认保存成功
- 获取JD列表，支持按分类筛选
- 更新JD内容，确认修改生效
- 删除JD，确认从数据库移除
- 多次使用同一个JD，确认使用次数正确递增
- 测试热门JD标记功能
- 访问Swagger文档确认所有端点文档完整
- 验证Pydantic校验生效
- 完成此里程碑后，更新 memory-bank/@architecture.md

---

### 步骤2.4：文档解析服务（Pipeline步骤1）

**目标：** 实现PDF/Word文档文本提取功能

**具体指令：**
1. 在 app/services/parser_service.py 中实现文档解析服务
2. 使用 unstructured 库解析PDF和Word文档
3. 对于需要OCR的PDF，集成 PaddleOCR
4. 实现文本提取和结构分析
5. 返回解析后的纯文本内容
6. 处理各种边界情况（损坏文件、加密文件等）
7. 在 app/schemas/ 中创建对应的Pydantic模型（严格校验所有输入输出）
8. 使用 HTTPException 处理异常，返回标准化 JSON 错误格式（参考 design-document.md 第10节）
9. 关键代码处添加简要注释
10. 确保 Swagger UI 文档自动生成且完整

**验证测试：**
- 解析标准PDF简历，确认能正确提取文本
- 解析Word文档（.docx），确认能正确提取文本
- 解析包含图片的PDF（需要OCR），确认能识别文字
- 测试损坏文件，确认返回适当错误信息
- 验证解析时间在合理范围内（一般<30秒）
- 验证所有Pydantic模型正常工作
- 验证错误处理和返回格式标准化
- 访问Swagger文档确认API文档质量
- 完成后考虑更新 memory-bank/architecture.md

---

### 步骤2.5：LLM结构化抽取服务（Pipeline步骤2）

**目标：** 使用LLM从文本中抽取出结构化的简历数据

**具体指令：**
1. 在 app/schemas/resume.py 中创建完整的Resume数据模型（与PPT模板字段对应）
2. 在 app/services/llm_service.py 中实现LLM调用服务（使用LiteLLM）
3. 在 app/services/extraction_service.py 中实现结构化抽取服务
4. 设计Prompt让LLM提取以下字段：
   - 个人信息（姓名、联系方式等）
   - 教育经历
   - 工作经历
   - 项目经验
   - 技能列表
   - 其他相关信息
5. 实现JSON格式输出验证

**验证测试：**
- 输入完整的简历文本，确认能生成完整的Resume对象
- 验证所有必填字段都被正确提取
- 测试边界情况（信息缺失的简历），确认能优雅处理
- 验证JSON输出格式正确，符合Pydantic模型定义
- 测试不同语言的简历（中文/英文）

---

### 步骤2.6：翻译与脱敏服务（Pipeline步骤3）

**目标：** 实现简历翻译和个人信息脱敏

**具体指令：**
1. 在 app/services/translation_service.py 中实现翻译服务
2. 使用LLM进行中文↔英文翻译
3. 在 app/services/anonymization_service.py 中实现脱敏服务
4. 识别并脱敏以下信息（参考 design-document.md 第4.5.2节）：
   - 真实姓名（替换为Mr/Ms. + 姓氏拼音）
   - 具体联系方式（电话、邮箱、年龄、出生日期、所在地 → 完全移除）
   - 公司名称（按出现顺序递增映射：Company A、Company B、Company C...）
   - 敏感个人信息
5. 保留职业经历和技能等关键信息
6. 在 app/schemas/ 中创建对应的Pydantic模型（严格校验所有输入输出）
7. 使用 HTTPException 处理异常，返回标准化 JSON 错误格式
8. 关键代码处添加简要注释
9. 确保 Swagger UI 文档自动生成且完整

**验证测试：**
- 测试中文简历翻译为英文，确认翻译质量
- 测试英文简历翻译为中文，确认翻译质量
- 验证姓名被正确替换（如：张伟 → Mr. Zhang）
- 验证联系方式被完全移除（不展示）
- 验证公司名称被正确递增映射
- 确认工作经历内容完整性不受影响
- 验证所有Pydantic模型正常工作
- 验证错误处理和返回格式标准化
- 访问Swagger文档确认API文档质量
- 完成后考虑更新 memory-bank/architecture.md

---

### 步骤2.7：约束性摘要服务（Pipeline步骤4）

**目标：** 对简历经历进行优化和摘要

**具体指令：**
1. 在 app/services/summarization_service.py 中实现摘要服务
2. 针对整个简历中的所有经历进行优化（参考 design-document.md 第4.5.3节）：
   - 修正语法错误、表达重复的地方
   - 统一格式和标点符号
   - 删除冗余或重复的工作内容
   - 每段经历使用相同的句式表达
   - 在不大幅改动候选人简历原文内容的基础上优化
   - 风格参考常见的简历风格
3. 在 app/schemas/ 中创建对应的Pydantic模型
4. 使用 HTTPException 处理异常，返回标准化 JSON 错误格式
5. 关键代码处添加简要注释
6. 确保 Swagger UI 文档自动生成且完整

**验证测试：**
- 输入长段落描述，确认经历被正确优化
- 验证语法和标点被统一修正
- 确认冗余内容被删除
- 验证所有经历句式风格统一
- 确认原文内容没有被大幅改动
- 验证所有Pydantic模型正常工作
- 验证错误处理和返回格式标准化
- 访问Swagger文档确认API文档质量
- 完成后考虑更新 memory-bank/architecture.md

---

### 步骤2.8：岗位匹配评估服务（Pipeline步骤5）

**目标：** 计算简历与JD的匹配度

**具体指令：**
1. 在 app/services/matching_service.py 中实现匹配服务
2. 提取JD中的关键词和要求
3. 分析简历中的技能和经验
4. 计算匹配度分数（0-100%）
5. 生成匹配分析报告，指出强项和待改进项
6. 识别简历中需要补充或强调的部分

**验证测试：**
- 输入匹配度高的简历+JD，确认分数>80%
- 输入匹配度低的简历+JD，确认分数<50%
- 验证匹配分析报告包含具体的强项和弱项
- 测试不同岗位的JD，都能给出合理分析
- 确认建议具有可操作性

---

### 步骤2.9：PPT模板填充服务（Pipeline步骤6）

**目标：** 将结构化数据填入PPT模板

**具体指令：**
1. 在 app/services/filler_service.py 中实现PPT填充服务
2. 使用 python-pptx 库操作PPT文件
3. 实现模板配置管理（app/services/template_config.py）
4. 定义Resume字段到PPT占位符的映射关系（参考 design-document.md 第4.5.1节）
5. 支持不同模板（纵向、横向）
6. 处理文本溢出和格式调整
7. 保持模板原有样式
8. 在 app/schemas/ 中创建对应的Pydantic模型
9. 使用 HTTPException 处理异常，返回标准化 JSON 错误格式
10. 关键代码处添加简要注释
11. 确保 Swagger UI 文档自动生成且完整

**验证测试：**
- 使用完整的Resume数据填充模板，确认生成PPT文件
- 验证所有字段都正确填入对应位置
- 检查生成的PPT样式是否与模板一致
- 测试不同模板（纵向、横向）都能正确填充
- 验证长文本能正确处理（换行、调整字号）
- 验证所有Pydantic模型正常工作
- 验证错误处理和返回格式标准化
- 访问Swagger文档确认API文档质量
- 完成后考虑更新 memory-bank/architecture.md

---

### 步骤2.10：Pipeline orchestration与任务管理

**目标：** 整合6个步骤，实现完整的处理流程

**具体指令：**
1. 在 app/services/pipeline_service.py 中实现Pipeline编排服务
2. 创建任务状态管理（app/models/task.py）
3. 实现异步任务处理（使用FastAPI后台任务）
4. 在 app/api/v1/process.py 中创建处理API：
   - POST /api/v1/process - 提交处理任务
   - GET /api/v1/process/{task_id} - 获取任务状态
   - GET /api/v1/process/{task_id}/result - 获取处理结果
5. 实现进度实时更新（每步完成后更新状态）
6. 实现错误处理和重试机制

**验证测试：**
- 提交完整的处理任务，确认任务创建成功
- 轮询任务状态，确认进度从0%到100%正确更新
- 验证Pipeline的6个步骤按顺序执行
- 最终获取生成的PPT文件，确认内容正确
- 测试错误场景（如损坏文件），确认返回适当错误
- 验证处理历史正确保存

---

### 步骤2.11：历史记录与统计API

**目标：** 实现历史记录查询和统计功能

**具体指令：**
1. 在 app/models/history.py 中创建HistoryRecord模型
2. 在 app/schemas/history.py 中创建历史记录相关模型
3. 在 app/services/history_service.py 中实现历史记录服务
4. 在 app/api/v1/history.py 中创建历史API：
   - GET /api/v1/history - 获取历史记录列表（支持分页、筛选）
   - GET /api/v1/history/{id} - 获取单条历史详情
   - GET /api/v1/history/{id}/download - 重新下载生成的PPT
   - DELETE /api/v1/history/{id} - 删除历史记录
   - GET /api/v1/history/statistics - 获取统计数据
5. 实现按时间、状态、模板类型等筛选

**验证测试：**
- 创建多个处理任务，确认历史记录正确保存
- 获取历史列表，支持分页和筛选
- 重新下载历史PPT，确认文件可访问
- 删除历史记录，确认从数据库移除
- 获取统计数据，确认总数、成功率、月度数据正确

---

## 阶段三：前端UI开发（后端计划中简要记录依赖关系）

**说明：** 此阶段主要由前端实施计划负责，后端主要提供API支持

---

## 阶段四：前后端联调与集成测试

> ⚠️ **重要**：此阶段是前后端协作的关键里程碑。完成此阶段后，前后端可独立修改各自的业务逻辑，但需遵守本章定义的 **API 契约** 和 **环境配置规范**。

---

### 步骤4.0：联调前置条件 — 环境变量与代理配置

**目标：** 建立前后端独立可切换的环境配置体系，确保开发/生产模式互不干扰

#### 4.0.1 后端环境变量

**具体指令：**
1. 在 `backend/.env` 中创建开发环境变量：
```env
# 服务配置
HOST=0.0.0.0
PORT=8000
DEBUG=true

# CORS 允许的前端地址（逗号分隔，生产环境需改为具体域名）
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# 文件上传配置
MAX_UPLOAD_SIZE_MB=10
UPLOAD_DIR=uploads
OUTPUT_DIR=output

# 数据库
DATABASE_URL=sqlite:///./data/resume.db

# LLM 配置
LLM_PROVIDER=litellm
LLM_MODEL=gpt-4o
```
2. 修改 `app/core/config.py`，从 `.env` 读取配置（使用 pydantic-settings）
3. 修改 `app/main.py`，使 CORS `allow_origins` 从配置读取而非硬编码 `["*"]`

> 💡 **独立修改保护**：后端修改端口/上传限制/CORS 白名单时，只需改 `.env`，前端无需感知。

**验证测试：**
- 修改 `.env` 中的 `PORT=8001`，重启后端确认端口切换生效
- 修改 `CORS_ORIGINS` 只保留 `http://localhost:9999`，确认其他来源请求被拒绝

#### 4.0.2 前端环境变量（✅ 已完成）

**具体指令（已完成）：**
1. ✅ 已创建 `frontend/.env.development`
2. ✅ 已创建 `frontend/.env.production`
3. ✅ 已修改 `frontend/src/api/request.ts`，从环境变量读取 baseURL

#### 4.0.3 Vite 代理配置验证（✅ 当前配置正确）

**当前配置**（`frontend/vite.config.ts`）：
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

---

### 步骤4.1：API 契约锁定 — 路径与格式对齐

**目标：** 确保前端调用路径与后端路由完全一致，消除双重前缀、路径不匹配等问题

#### 4.1.1 后端路由规范（当前状态核对）

| 模块 | 路由前缀 | 完整示例 |
|------|----------|----------|
| 根路由 | `/api/v1` | `app.include_router(api_router, prefix="/api/v1")` |
| 简历处理 | `/api/v1/resume` | `POST /api/v1/resume/upload` |
| 任务编排 | `/api/v1/process` | `POST /api/v1/process` |
| 模板管理 | `/api/v1/template` | `GET /api/v1/template/list` |
| 术语表 | `/api/v1/termbase` | `GET /api/v1/termbase` |
| 健康检查 | `/health` | `GET /health` |

> 📋 **契约原则**：所有业务 API 统一挂载在 `/api/v1/` 下，非业务端点（`/health`、`/docs`）不在其下。

#### 4.1.2 前端 API 路径验证（✅ 已完成修复）

**当前状态**：`frontend/src/api/request.ts` 中 `baseURL` 已使用 `import.meta.env.VITE_API_BASE_URL || '/api/v1'`；`frontend/src/api/index.ts` 中所有路径已修正为 `/resume/`、`/process/`、`/template/` 等相对路径，与 `baseURL` 拼接后完整匹配后端路由，无双重 `/api/v1/` 前缀。

#### 4.1.3 请求/响应格式契约

**前端→后端请求格式**（与 design-document.md §10 对齐）：
```ts
// 成功响应接口（所有 API 统一使用）
interface ApiResponse<T = any> {
  success: boolean
  data: T
  message: string
  timestamp: string
}

// 分页列表响应
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

**后端→前端错误格式**（与 design-document.md §10.1 对齐）：
```json
{
  "success": false,
  "error_code": "VALIDATION_ERROR",
  "message": "请求参数验证失败",
  "details": { ... },
  "timestamp": "2026-07-06T10:30:00Z"
}
```

> 💡 **独立修改保护**：前后端均依赖此接口格式。后端修改字段时必须同步更新 Swagger 文档（前端以此为准）；前端修改类型定义时必须与后端 Swagger 文档对齐。

---

### 步骤4.2：文件上传联调

**目标：** 验证前端上传→后端接收→返回文件ID 的完整链路

**具体指令：**
1. 确认后端上传端点：`POST /api/v1/resume/upload`（multipart/form-data，字段名 `file`）
2. 确认前端上传调用（`resumeApi.upload`）使用 `FormData`，Content-Type 自动设为 `multipart/form-data`
3. 联调验证项：
   - PDF 文件上传成功，返回 `file_id`
   - Word 文件上传成功
   - 文件超过 10MB 时返回 `FILE_SIZE_EXCEEDED` 错误
   - 不支持的文件类型返回 `FILE_TYPE_INVALID` 错误
4. 确认上传进度反馈（前端显示上传状态）

> 💡 **独立修改保护**：文件大小上限在 `backend/.env` 的 `MAX_UPLOAD_SIZE_MB` 中配置；前端上传进度条可独立调整 UI，不影响后端。

**验证测试：**
- 上传 PDF 文件（<10MB），确认前端收到 `{"success":true, "data":{"file_id":"xxx"}}`
- 上传 >10MB 文件，确认前端显示错误提示"文件大小超出限制"
- 上传 .exe 文件，确认前端显示"不支持的文件类型"
- F12 Network 确认请求为 `multipart/form-data`，Content-Type 不含手动设置的 application/json

---

### 步骤4.3：Pipeline 提交与轮询联调

**目标：** 验证前端提交任务→后端异步处理→前端轮询状态 的完整链路

**具体指令：**
1. 确认后端端点：
   - `POST /api/v1/process` — 提交任务（请求体含 `file_id`、`template_type`、`target_language` 等）
   - `GET /api/v1/process/{task_id}` — 轮询状态
   - `GET /api/v1/process/{task_id}/result` — 获取结果
2. 前端联调验证项：
   - 提交任务后立即收到 `task_id`
   - 轮询间隔设为 2-3 秒（避免过度请求）
   - 处理进度页面正确展示 5 个 Pipeline 步骤状态
   - 每步完成后 `percentage` 正确递增
   - 任务完成/失败时前端停止轮询
   - 处理失败时显示错误信息 + 重试按钮

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

> 💡 **独立修改保护**：轮询间隔由前端独立控制（在 Pinia store 中配置）；Pipeline 步骤数/顺序由后端独立控制，前端动态渲染 `steps` 数组（不硬编码步骤数量）。

**验证测试：**
- 提交任务 → 前端跳转进度页 → 轮询开始
- 观察 5 个步骤依次从 `pending` → `in_progress` → `completed`
- 进度条从 0% 平滑增长到 100%
- 处理完成后自动跳转到结果预览页
- 手动中断后端 → 前端显示网络错误提示，不白屏

---

### 步骤4.4：PPT 下载联调

**目标：** 验证文件下载链路（blob 处理、中文文件名、双格式支持）

**具体指令：**
1. 确认后端下载端点：
   - `GET /api/v1/resume/fill/download/{filename}?format=pptx`
   - `GET /api/v1/resume/fill/download/{filename}?format=pdf`
   - 响应头：`Content-Disposition: attachment; filename*=UTF-8''xxx.pptx`（RFC 5987 编码）
2. 前端下载实现要求：
   - 使用 `responseType: 'blob'` 接收二进制数据
   - 从 `Content-Disposition` 头解析文件名（优先用 `filename*=` UTF-8 编码）
   - 使用 `URL.createObjectURL(blob)` + `<a download>` 触发下载
   - 下载完成后 `URL.revokeObjectURL()` 释放内存
3. 联调验证项：
   - PPTX 下载文件名正确（含中文，如 `IAV_Mr.Zhang_HUD_Resume_EN.pptx`）
   - PDF 下载正常
   - 文件可正常打开，内容完整
   - 无中文文件名乱码

> 💡 **独立修改保护**：文件命名规则由后端 `SmartFillerService` 控制；前端只负责 blob 下载，不构造文件名。后端修改命名规则时前端无需改动。

**验证测试：**
- 处理完成后点击"下载 PPTX"，确认文件下载成功且内容正确
- 点击"下载 PDF"，确认 PDF 下载成功
- 检查下载的文件名是否正确（中文无乱码）
- F12 Console 无 blob URL 内存泄漏警告

---

### 步骤4.5：模板库 & JD库 & 历史记录 管理功能联调

**目标：** 验证 CRUD 管理功能前后端连通

**具体指令：**
1. 模板库联调：
   - `GET /api/v1/template/list` → 前端列表渲染正确
   - `POST /api/v1/template/upload` → 上传新模板+刷新列表
   - `DELETE /api/v1/template/{id}` → 删除+二次确认+列表刷新
2. JD 库联调：
   - `GET /api/v1/jd/list` → 分类筛选 + 分页
   - `POST /api/v1/jd/create` → 创建成功回显
   - `PUT /api/v1/jd/{id}` → 编辑保存
3. 历史记录联调：
   - `GET /api/v1/history/list` → 分页 + 状态筛选
   - `GET /api/v1/history/statistics` → 统计卡片数据正确
   - `DELETE /api/v1/history/{id}` → 删除后列表刷新

> 💡 **独立修改保护**：每类资源的管理接口路径和字段名必须锁定；后端新增字段时遵循"向后兼容"原则（不删除已有字段、新增字段用可选类型）；前端新增展示字段时不影响已有功能。

**验证测试：**
- 每个 CRUD 操作均返回正确的 `ApiResponse` 格式
- 创建→列表刷新→编辑→列表刷新→删除→列表刷新 全流程走通
- 网络错误时前端显示 ElMessage 错误提示，不崩溃

---

### 步骤4.6：联调 Checklist（一次性全部验证）

完成以上所有步骤后，执行此完整 Checklist：

| # | 检查项 | 方法 |
|---|--------|------|
| 1 | 前端启动（`pnpm dev`，端口3000） | 浏览器访问 `localhost:3000` |
| 2 | 后端启动（`python run_server.py`，端口8000） | 浏览器访问 `localhost:8000/docs` |
| 3 | CORS 正常（前端能调后端 API） | F12 Network 无 CORS 报错 |
| 4 | Vite 代理生效（请求经 `:3000/api` → `:8000`） | Network 面板 Request URL 显示 `localhost:3000/api/...` |
| 5 | 健康检查 `GET /api/v1/health` 返回 200 | curl 或浏览器直接访问 |
| 6 | 文件上传正常 | 从首页上传 PDF/Word |
| 7 | Pipeline 提交+轮询正常 | 提交后进度页步骤依次更新 |
| 8 | PPT 下载正常（含中文文件名） | 下载后文件可打开、文件名正确 |
| 9 | 模板库 CRUD 正常 | 增删改查全流程 |
| 10 | JD 库 CRUD 正常 | 增删改查+分类筛选 |
| 11 | 历史记录列表+统计正常 | 分页+筛选+统计卡片 |
| 12 | 错误处理正常 | 断开后端→前端不白屏，显示错误提示 |

---

### 步骤4.7：接口版本化策略（预防性措施）

**目标：** 为未来 API 变更预留平滑升级路径

**策略：**
1. **URL 版本化**：当前所有 API 在 `/api/v1/` 下。未来 breaking change 使用 `/api/v2/`，旧版本保留至少一个大版本周期。
2. **字段向后兼容**：
   - 新增字段：始终设为可选（`Optional` / `?`），前端按缺省值处理
   - 删除字段：先标记 `@deprecated`，保留至少一个版本后再移除
   - 重命名字段：新旧字段并存一个版本，前端逐步迁移
3. **前端类型同步**：每次后端 Swagger 文档更新后，手动更新 `frontend/src/types/index.ts` 中的对应接口

> 💡 **独立修改保护**：后端新增 `/api/v2/` 不影响前端对 `/api/v1/` 的调用；前端迁移到 v2 时只需修改 API 函数中的路径，不影响 UI 组件。

---

### 步骤4.8：性能优化（后端补充）

**目标：** 优化响应时间

**具体指令：**
1. 分析各 Pipeline 步骤耗时（当前实测约 111s，LLM 调用占 100s+）
2. 为高频查询添加数据库索引
3. 文件列表查询结果缓存（5 分钟 TTL）
4. 前端添加加载骨架屏（skeleton）

**验证测试：**
- 完整处理时间 ≤ 2 分钟（目标）
- API 列表查询响应 < 500ms

---

## 阶段五：文档与部署

### 步骤5.1：完善开发文档

**目标：** 确保文档完整准确

**具体指令：**
1. 更新 backend/README.md，包含：
   - 环境配置步骤
   - 数据库初始化
   - 运行命令
   - API文档访问地址
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
1. 配置后端生产环境变量
2. 编写后端启动脚本
3. 配置日志收集
4. 配置数据备份策略

**验证测试：**
- 后端能以生产模式启动
- 所有功能在生产配置下正常工作
- 日志正确输出
- 确认数据备份机制可用

---

## 实施顺序总结

```
阶段一：基础架构
  ↓
步骤1.1 后端初始化 → 步骤1.2 前端初始化（依赖） → 步骤1.3 数据库配置
  ↓
阶段二：后端API
  ↓
步骤2.1 文件上传 → 步骤2.2 模板库API → 步骤2.3 JD库API
  ↓
步骤2.4 文档解析 → 步骤2.5 LLM抽取 → 步骤2.6 翻译脱敏
  ↓
步骤2.7 摘要服务 → 步骤2.8 匹配评估 → 步骤2.9 PPT填充
  ↓
步骤2.10 Pipeline编排 → 步骤2.11 历史记录API
  ↓
阶段三：前端UI（依赖）
  ↓
阶段四：测试优化
  ↓
步骤4.1 端到端测试 → 步骤4.2 性能优化 → 步骤4.3 错误处理优化
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
| M2：管理功能完成 | 模板库和JD库的后端API完成 |
| M3：Pipeline完成 | 6个处理步骤全部实现并能串联运行 |
| M4：UI完成 | 前端所有页面完成（前端里程碑） |
| M5：集成完成 | 端到端流程能完整跑通 |
| M6：发布就绪 | 文档完善，可部署生产 |

---

## 关键规范补充（基于 .github/copilot-instructions.md）

### 后端开发强制规范
1. **Pydantic严格校验** - 所有请求体、查询参数、响应体必须使用Pydantic模型定义和校验
2. **标准化错误处理** - 统一使用FastAPI的HTTPException，返回标准化JSON错误格式
3. **分层架构** - 严格遵循 api(routers) → services → models/schemas 的分层
4. **Swagger文档** - 确保自动生成的Swagger UI文档（/docs）质量高、清晰易用
5. **代码注释** - 在关键代码处添加简要注释
6. **架构图** - 完成重要模块后，补充服务架构图（mermaid或ASCII）
7. **数据库模式** - 完成数据模型后，补充具有关键关系的数据库模式图

---

## 注意事项

1. **严格按顺序执行** - 每个步骤依赖前序步骤完成
2. **每步必须验证** - 完成一步后立即执行验证测试，确认无误再继续
3. **保持代码质量** - 遵循项目编码规范
4. **及时更新文档** - 如发现设计文档需要更新，及时修改
5. **小步快跑** - 每个步骤都是小目标，便于验证和调整
6. **规范强制执行** - 所有后端规范必须遵守，不能妥协
