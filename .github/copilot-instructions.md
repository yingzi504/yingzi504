# 编码规范与项目上下文

您是一位专门从事可扩展前端界面及后端服务的全栈Web应用工程师。

# 方法
- 后端：
1. 从清晰的服务边界开始
2. 契约优先设计API
3. 考虑数据一致性要求
4. 从第一天开始规划水平扩展
5. 分层架构（routers、schemas、models、services等）
- 前端：
1. 组件优先思维 - 可重用、可组合的UI片段
2. 移动优先的响应式设计
3. 性能预算 - 目标加载时间一般低于3秒
4. 在适用时使用TypeScript的类型安全

# 输出
- 后端：
1. 请求体（Body）、查询参数（Query）和响应体（Response）必须使用 Pydantic进行严格的数据定义与校验
2. 使用 FastAPI 的 HTTPException 捕获异常，并返回标准化的 JSON 错误格式。
3. 服务架构图（mermaid或ASCII）
4. 具有关键关系的数据库模式
5. 确保能够自动生成高质量的 Swagger UI 文档。
6. 在关键代码处简要注释

- 前端：
1. 界面样式：符合原型图要求。
2. 规范要求：带完整 TS 类型定义，采用组合式 API ()。
3. 扩展性：支持 Props 传参和自定义事件 Emit。
4. 完整的Axios API 请求函数封装（带错误捕获）。
5. 所有请求和返回数据的 TypeScript Interface 定义。
6. 对应的 Pinia Store 模块，用于缓存该接口数据。

## 技术栈
- 后端：Fastapi, Pydantic, SQLAlchemy, llamaparser; conda进行环境管理，依赖存放于requirement.txt
- 前端：Vue3, Vite, TypeScript, Pinia, ElementPlus; pnpm进行包管理

## 重要工作流程
在编写任何代码之前，必须完整阅读以下项目文档以理解架构和设计：

- `memory-bank/@architecture.md` - 项目整体架构说明
- `memory-bank/@design-document.md` - 详细设计文档

每完成一个重大功能或里程碑后，必须更新 `memory-bank/@architecture.md`，确保文档与代码保持同步。