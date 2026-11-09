# CV 生成规范与需求登记

最后核对：2026-09-29。范围：上传简历后的 CV 转换，不包括 JD 生成。

本文件是人工查阅与需求管理入口，不是程序自动执行的脚本。规则编号保持稳定；修改规则时同时更新实现和验证记录。聊天中的新要求需落到实现后才生效。

## 执行入口与生效方式

| 位置 | 用途 | 生效方式 |
|---|---|---|
| `backend/app/core/cv_rules.py` | 共用规则默认值：输入长度、翻译次数、正文字号、模块间距、未知学位文案 | 后端启动时加载；修改后重启 |
| `backend/app/prompts/cv_extraction.txt` | 简历抽取的模型指令 | 每次结构化抽取时读取；已在进行的调用不受影响 |
| `backend/app/services/translator_service.py` | 翻译提示、字段策略、术语和质量复核 | 修改代码后重启 |
| `backend/app/services/summarization_service.py` | 摘要提示、工作与项目组织、内容清洗 | 修改代码后重启 |
| `backend/app/schemas/education.py` | 确定性学位规范 | 修改代码后重启 |
| `backend/app/services/smart_filler_service.py` | 模板、分页、字体和文件输出 | 修改代码后重启 |
| `backend/app/services/pipeline_service.py` | 上述规则的执行顺序与最终出口 | 修改代码后重启 |
| `backend/app/core/config.py`、`backend/.env` | 上传大小、模型连接等运行环境配置 | 修改后重启；不要在规范配置中复制密钥 |

状态说明：**代码执行**表示存在确定性处理；**模型指令**表示提示词要求，不保证每次模型输出完全符合；**待实现**不能对用户宣称已生效。既有功能与本次测试覆盖也须区分。

## 输入与真实性

| 编号 | 要求与边界 | 状态／实现 |
|---|---|---|
| CV-IN-01 | 接受 PDF、DOCX、DOC，拒绝空文件；当前后端配置 10 MB。界面图片／20 MB 提示与后端不一致，待修正 | 代码执行；`api/resume.py`、`core/config.py` |
| CV-IN-02 | 结构化抽取模型输入上限 12000 字符，超长截断；不能承诺超长资料完全无遗漏 | 代码执行；`CV_RULES.extraction_max_input_chars`、`extractor_service.py` |
| CV-FACT-01 | 所有事实来自原文，不虚构经历、技能、工具、数字、成果或管理范围；缺失信息留空 | 模型指令；提取、翻译、摘要服务 |
| CV-FACT-02 | 教育、工作、项目经历按时间倒序；原文有教育章节时必须尝试提取 | 模型指令；`prompts/cv_extraction.txt` |
| CV-FACT-03 | 恢复嵌套的有日期项目及原文工作经历；项目缺失公司／职位可按已有工作时间线匹配；清理空项目、无意义时段和误混入的章节标题 | 代码执行；`summarization_service.py`、`pipeline_service.py` |

## 经历、技能与工龄

| 编号 | 要求与边界 | 状态／实现 |
|---|---|---|
| CV-EXP-01 | 抽取时逐条保留不同职责，不合并、不遗漏，分号分隔；超过500字的项目详述可概括，保留技术细节与成果 | 模型指令；`cv_extraction.txt` |
| CV-EXP-02 | 工作写岗位概述、项目保留细节；有相关项目时工作概述2—4条，写职责／能力／范围／责任，不重复项目名、日期和逐步实施细节 | 模型指令及结构处理；`summarization_service.py` |
| CV-EXP-03 | 无关联项目的工作经历按原职责优化；不同独立职责不合并，去除完全重复项和冗余修饰；保留核心职责及关键成果 | 模型指令及清洗；`summarization_service.py` |
| CV-EXP-04 | 用动词开头、修正语法，单条以1—2行为写作目标；模型不添加序号、项目符号、前缀或说明，由排版统一处理 | 模型指令；1—2行不是实际渲染硬上限 |
| CV-SKILL-01 | 检查全篇工作、项目、自评及技能章节；归纳明示使用的技术、方法、协议、工具，不只列工具；去重，不因语言或长度删减技能范围 | 模型指令；`cv_extraction.txt` |
| CV-SKILL-02 | 技能以分号组织；语言技能保留语言名称及水平 | 模型指令及模型字段兼容处理 |
| CV-SKILL-03 | CV底部技术技能仅保留原文明确出现的软件、应用程序、工程工具或具名平台名称；排除编程语言、框架、库、协议、方法、硬件、技术领域、泛化能力及模型推断项。模型负责发现候选项，代码逐项核对原文证据、过滤常见非软件类别并用受控软件词表补漏；本规则取代CV-SKILL-01对`tech_skills`的宽口径要求，语言技能仍按CV-SKILL-02处理 | 模型指令＋确定性证据校验；`prompts/cv_extraction.txt`、`extractor_service.py`；已接入，开放名称的类别判断仍有模型边界 |
| CV-TIME-01 | 原文有数字总工龄时优先保留，仅规范单位；缺失时按工作月份并集计算，重叠不重复，无有效时间线则留空 | 代码执行；`TranslatorService.normalize_total_experience` |
| CV-TIME-02 | 日期规范为年月区间，至今按中文／Present输出；当前仅年份区间会补为起年01月至止年12月，属于既有实现假设 | 代码执行；`TranslatorService.normalize_period` |

## 教育与学位

| 编号 | 要求与边界 | 状态／实现 |
|---|---|---|
| CV-EDU-01 | 教育输出限定时间、学校、学位、专业；学位字段本科→学士、硕士研究生→硕士、博士研究生→博士 | 代码执行；`schemas/education.py`、`EducationItem`、pipeline、smart filler |
| CV-EDU-02 | 单写研究生无法确定层级时显示“学位未注明”；不得自动猜成硕士 | 代码执行；`CV_RULES.ambiguous_degree_label` |
| CV-EDU-03 | 保留学科及在读状态；专科不擅自升级；现有英文学位保持英文，语言本地化由翻译阶段负责 | 代码执行／翻译指令 |
| CV-EDU-04 | 用户要求禁止本科／研究生表述；目前只在教育学位字段实现，不是摘要、专业等全文禁词。进一步扩大范围应避免改坏学校名称或原文事实 | 部分实现，全文范围待明确与接入 |

## 语言与岗位

| 编号 | 要求与边界 | 状态／实现 |
|---|---|---|
| CV-TR-01 | CV支持中文／英文及纵向／横向模板；模板语言优先，目标岗位语言须与输出一致 | 代码执行；前端、`api/process.py`、`template_config.py` |
| CV-TR-02 | 全部自然语言字段翻译为目标语言，包括机构、学校、学院、项目业务名、学位、专业、职责、语言水平及数字单位 | 模型指令及残留检查；`translator_service.py` |
| CV-TR-03 | 机构优先官方译名，其次通行译名，否则合理音译／意译，不编造机构事实；中文机构及学位不附英文原名 | 模型指令 |
| CV-TR-04 | 技术缩写、工具、产品、协议、型号、正文部门／地区代码可保留；不能据此保留整段外文业务描述；使用术语库，保持格式、正式语气，不输出Markdown或解释 | 模型指令及字段策略 |
| CV-TR-05 | 单次翻译最多3次尝试（包括首轮）；达到上限保留最近非空结果继续，不是强制零漏译 | 代码执行；`CV_RULES.translation_max_attempts` |
| CV-JOB-01 | 模板技术领域只来自用户目标岗位，未填则空，不从经历猜测；填写时生成岗位及英文命名字段 | 代码执行；`pipeline_service.py` |
| CV-JOB-02 | 完整JD匹配评分／定向改写尚未接通；当前matching步骤跳过，界面存在JD输入不代表已执行匹配 | 待实现 |

## 脱敏与性别

| 编号 | 要求与边界 | 状态／实现 |
|---|---|---|
| CV-PRIV-01 | 中文姓名→姓＋先生／女士；英文→Mr./Ms.＋姓氏拼音；移除电话、邮箱、年龄、生日、所在地字段 | 代码执行；`anonymizer_service.py`；不等同于全文自由文本隐私扫描 |
| CV-PRIV-02 | 保留公司实体、工作、技能、教育；公司不替换为Company A/B，允许按目标语言翻译 | 代码执行及模型指令 |
| CV-GENDER-01 | 原文明确性别时直接采用，缺失或冲突弹窗确认，不以姓名／照片猜测，文件名及正文统一 | **已接入CV流程**；`gender_service.py`、`cv_gender_confirmation.py`、pipeline、`POST /process/{task_id}/gender`、UploadView与processing store |
| CV-GENDER-02 | CV在脱敏前强制取得原文明确性别或用户选择，不再走姓名猜测／默认男性分支；确认复用解析数据、并发只接受一次，非法或重复提交拒绝 | 已实现并验证。任务仍存于内存，服务重启或页面刷新后不提供本次任务的自动恢复；诊断用独立脱敏接口仍保留旧兼容逻辑 |

## 排版与文件

| 编号 | 要求与边界 | 状态／实现 |
|---|---|---|
| CV-LAYOUT-01 | 工作→项目→教育→技能；按实际内容高度分页，长内容续页，不强制所有简历一页 | 代码执行；`smart_filler_service.py` |
| CV-LAYOUT-02 | 字体Arial；正文表格12pt，页脚公司信息保留模板字号；非表格保留层级，小于9pt提升11pt | 代码执行；`CV_RULES.body_font_size_pt`；不是所有文本同字号 |
| CV-LAYOUT-03 | 模块间距0.5cm；普通页纵向3.74—26.47cm，末页预留页脚时3.74—23.54cm；按换行留安全余量 | 代码执行；`CV_RULES.module_spacing_cm`、`PageConstraints`；模板适配仍需视觉验证 |
| CV-LAYOUT-04 | 清理空技能标题、空段及尾部空页；公司块只在末页，空间不足省略，不为公司块单独增页 | 代码执行 |
| CV-LAYOUT-05 | 生成后记录PPT校验结果；不是所有校验问题都会阻止输出 | 代码执行；`pptx_validator.py`、pipeline |
| CV-OUT-01 | 主输出可编辑PPTX；PDF优先使用LibreOffice转换，Windows未安装LibreOffice时回退到本机Microsoft PowerPoint原生导出；两者均不可用时返回明确环境错误 | 代码执行；smart filler／`pdf_converter.py` |
| CV-OUT-02 | 下载文件名为`IAV_称谓姓氏_岗位_Resume_语言_日期.pptx`，PDF同名；删除随机字符尾缀，保留日期。内部存储使用唯一标识，归档按任务隔离以避免覆盖 | 已接入；`cv_rules.cv_download_filename`、smart filler、pipeline、下载及归档接口 |
| CV-OUT-03 | 分页复制形状时必须同步 OOXML 关系；输出不得含悬空 `r:id/r:embed/r:link`。保存前删除不承载可见内容的 Office `p:tags` 元数据，但必须保留形状必需的 `p:nvPr`；图片、超链接等可见内容关系缺失必须失败。PPTX 下载禁止缓存旧副本，禁止归档需 PowerPoint Repair 的文件 | 代码执行；`smart_filler_service.py` 关系感知复制与标签清理、`pptx_validator.py` 包完整性校验、下载接口 `Cache-Control: no-store`、`pipeline_service.py` 阻断归档 |
| CV-OUT-04 | CV 的 PDF 下载必须可从已归档 PPTX 按需生成并持久化；历史只归档 PPTX 时仍展示 PDF 操作，转换环境不可用时返回明确原因。Windows PowerPoint回退通过独立PowerShell进程和短临时路径导出，兼容PowerPoint 2007 | 代码执行；`pdf_converter.py`、`access_service.py`、`process.py`、`pipeline_service.py`、`CVLibraryView.vue` |

## 后续新增需求怎么处理

用户只需用文字描述目标，最好提供正反例及适用范围。不需要指定代码路径。

1. 在此登记新编号、要求、范围、与既有规则冲突、状态“待实现”。
2. 参数修改进入`cv_rules.py`；提取模型指令进入`prompts/cv_extraction.txt`。
3. 复杂抽取、清洗、翻译、排版规则修改对应现有服务；跨前后端交互同时修改接口、状态、页面。
4. 只有出现独立、可复用的职责才新增模块，不为每条要求建一个代码存放点。
5. 执行相关测试；输出布局变化增加视觉检查；记录真实验证范围。
6. 检查活跃任务后重启需要加载新代码的后端，验证健康接口，再标记已接入。历史生成文件不会自动重写。

需求登记模板：`编号｜用户要求与示例｜适用范围｜执行方式｜实现位置｜状态｜验证证据｜日期`。

## 验证与变更记录

- 2026-09-22：学位字段规范接入；`tests/test_degree_wording.py`覆盖10例。性别识别器`tests/test_source_gender.py`覆盖8例，但未接入交互。
- 2026-09-29：建立本规范、根目录`AGENTS.md`维护约定、共用规则配置；原样迁移抽取提示词并连接调用点。原有默认值不变，翻译与摘要提示仍在服务中，尚未全部外置。
- 本轮验证结果见本次交付说明；新增配置与提示词测试位于`tests/test_cv_rules.py`。


### 2026-09-29 validation evidence

- Command: `python -m pytest tests/test_cv_rules.py tests/test_degree_wording.py tests/test_source_gender.py -q`
- Result: 25 passed; one existing `asyncio_mode` configuration warning (pytest-asyncio absent). These tests are synchronous.
- Changed Python modules passed compileall. Prompt files are included by the existing Docker COPY rule.
- Backend restarted after confirming zero active tasks.
- No live LLM conversion or PPT visual regression was run for this behavior-preserving refactor.


### 2026-09-29 性别确认流程交付

- 主流程在解析与提取后检查原文性别；缺失／冲突返回 awaiting_input。用户必选男／女后继续原任务；不再次调用解析、提取模型。
- 前端中英文弹窗无默认选择；失败保留选择并可重试，确认后重新轮询；任务进行及等待时禁止切换CV/JD模式。
- `test_cv_gender_confirmation.py`覆盖并发单次确认、非法值、原文覆盖模型猜测；`test_cv_gender_pipeline.py`验证在脱敏前暂停及解析复用。
- `test_cv_gender_output.py`覆盖中文／英文×男／女×纵向／横向×原文明确／手动确认共16种组合，实际生成PPTX并读取正文及文件名，同时验证接口404、409、422。
- 连同原文识别、学位规范，共41项测试通过。输出测试模拟解析和提取结果，实际执行脱敏、姓名翻译及模板填充；未调用真实LLM，也未验证PDF转换。
- 浏览器通过模拟API验证必选、女性提交值、500失败保留、重试完成；发现并修复等待区域误用JD地点提示。截图：`output/playwright/gender-dialog.png`。


### 2026-09-29 账号、操作记录与文件访问

| 编号 | 范围及要求 | 实现位置 | 状态与验证 |
| --- | --- | --- | --- |
| CV-ACCESS-01 | CV 处理需登录、完成初始改密并具备 CV 功能权限；原始上传及任务只能由所属用户或管理员访问 | `api/access.py`、`api/process.py`、`services/access_service.py` | 已接入；`tests/test_access_control.py` 验证匿名拒绝、跨用户访问拒绝与功能权限 |
| CV-AUDIT-01 | 记录账号、操作时间、接口、结果码及关联任务；后台可检索 | `models/access.py`、`api/access.py`、`services/access_service.py` | 已接入；测试验证登录、任务状态和下载事件，不记录密码或请求正文 |
| CV-ARCHIVE-01 | CV 完成文件按任务编号归档；登录用户仅调取本人文件，管理员可调取全部；启用前文件仅管理员可访问 | `services/pipeline_service.py`、`services/access_service.py`、`api/access.py` | 已接入；测试验证源输出覆盖后归档保留、文件路径边界及历史隔离 |

账号、权限、后台使用与首次管理员创建方式见 [账号与后台管理](账号与后台管理.md)。此功能不改变 CV 内容生成规范。原进行中任务仍不能跨后端重启恢复，重启后会标记中断；完成文件已可持久调取。

- CV-UI-01：处理进度百分比仅由进度条单独显示，后端步骤说明不重复拼接百分比。

### 2026-09-29 进度与下载文件名修复

- 后端步骤消息不再拼接百分比，由前端进度条统一显示。
- PPTX/PDF 下载及新归档名称移除日期后的 12 位随机字符；内部源文件保留唯一标识防覆盖，旧归档与历史文件下载时同样清理名称，不重写历史文件。
- PDF 可用性根据实际存储路径检查，不根据显示名称推算。
- `test_cv_output_names.py`、`test_cv_gender_output.py`、`test_access_control.py` 共 26 项通过，覆盖同名输出防覆盖、PDF 可用性检测、进度、历史及归档下载、实际 PPTX 性别输出和访问控制。本次未运行真实 PDF 转换。
- 无活跃任务时重启后端，健康检查通过。

### 2026-11-05 CV 库与部门归档

| 编号 | 用户要求与范围 | 执行方式 | 实现位置 | 状态 | 验证证据 |
| --- | --- | --- | --- | --- | --- |
| CV-ARCHIVE-02 | CV 转换完成后自动进入 CV 库；按 JD 转换使用的固定部门目录分类，并可按目标岗位筛选；历史无部门记录显示为未分类 | 确定性执行：任务创建时保存部门与岗位，完成后沿用既有归档流程；CV 库接口按部门／岗位查询 | `models/access.py`、`models/migrations.py`、`services/access_service.py`、`api/access.py`、`frontend/src/views/CVLibraryView.vue` | 已接入并验证 | `test_access_control.py` 覆盖部门分类、岗位筛选、成员数据隔离和下载；相关 17 项测试通过。迁移后 13 条旧 CV 均保留且归入未分类；健康检查、OpenAPI 与前端路由均为 200 |
| CV-UI-02 | CV 处理阶段部门为必选项，目录与 JD 转换共用固定 `DEPARTMENT_CODES`，未选择不得提交 | 确定性执行：前端提交前校验；后端请求 schema 再做必填和固定字典校验 | `frontend/src/views/UploadView.vue`、`frontend/src/stores/processing-advanced.ts`、`schemas/task.py`、`api/process.py` | 已接入并验证 | 前端 `pnpm build` 通过；测试验证缺失／非法部门返回 422、合法 `TV-X1` 可提交。Playwright CLI 未能保持本机浏览器会话，未完成截图式视觉回归 |

### 2026-11-05 PowerPoint Repair 问题修复

- 根因：分页时直接深拷贝形状 XML，形状中的 Office 标签仍引用源页 `rId`，目标页未建立对应关系；PowerPoint 因悬空关系要求 Repair，并可能删除关联形状造成内容缺失。
- 修复：复制形状时同步标签、图片和超链接关系；保存前清理仅限不可见且已悬空的 Office 标签；验证器新增确定性包关系检查，流水线对包错误直接失败，不再归档。
- 历史数据：扫描 19 份 CV 归档，目标文件修复后另有 18 份受影响；已逐份备份为 `.broken-backup` 并修复。每份修复均要求页数及全部文本／表格内容一致且包错误归零。
- 验证：`test_pptx_relationship_integrity.py` 覆盖损坏检测、关系感知复制、无内容丢失清理及空关系属性兼容；相关 CV 输出、文件名和分页回归共 29 项通过。目标吴先生文件 2 页、8 个文本对象修复前后一致，独立包检查从 3 个错误降为 0。因本机 PowerPoint 自动化与渲染依赖不可用，未完成原生 PowerPoint 打开和截图验证。

### 2026-11-06 PowerPoint Repair 兼容性补充修复

- 根因补充：公司信息表格仍有一条原始 XML 深拷贝路径，没有同步关系；旧清理逻辑只处理悬空标签且可能错误删除标签父级。即使基础关系检查通过，跨页复用的 Office `p:tags` 元数据仍会在部分 PowerPoint 版本中触发 Repair。固定下载 URL 也可能让浏览器复用修复前文件。
- 修复：公司表格改用关系感知复制；保存前删除全部不可见 `p:tags` 及其未使用关系，只删除标签本身并保留必需 `p:nvPr`；CV 下载响应增加 `Cache-Control: no-store`。
- 历史数据：32 份归档全部移除 Office 标签，并为每份保留 `.compat-backup`。每份替换均要求页数、全部文本及表格内容一致、关系错误为零。修复后复扫：32 份标签为零、缺失 `p:nvPr` 为零、包关系错误为零。
- 验证：PPTX 关系、实际 CV 中英文／横竖版、文件名与分页回归共 31 项通过；两个吴先生归档均通过本机 PowerPoint COM 原生打开（各 2 页），未弹出 Repair。仍建议同事删除旧下载文件并重新下载验证其 PowerPoint 版本。

### 2026-11-06 CV底部软件技能收窄

- `CV-SKILL-03` 已接入：抽取提示词仅要求软件、应用程序、工程工具或具名平台；抽取服务逐项验证模型候选名称在原始解析文本中出现，删除无证据项及受控排除表中的语言、框架、协议、方法、硬件等，并用受控软件词表从原文补漏。
- 确定性边界：原文证据核验、受控排除表、受控软件词表及去重由代码执行；未收入词表的新名称是否属于软件仍依赖模型分类，不能把提示词描述为绝对保证。超过12000字符的模型输入仍可能漏掉开放名称，但受控词表补漏扫描完整解析文本。
- 验证：精确回归集14项通过，覆盖CANoe／ADB回退、Python／Linux／CAN／Agile排除、Jira保留、虚构候选删除、CANoe名称标准化、Microsoft Office补漏、普通`office`词义消歧、LLM失败回退、提示词加载、逐项翻译与大小写去重。扩展相关测试共31项通过、1项既有翻译断言失败；失败项要求英文公司名在中文输出中保持不译，与当前`CV-TR-02/03`要求机构名本地化冲突，与本次技能改动无关。

### 2026-11-06 CV PDF PowerPoint回退修复

- 根因：本机未安装LibreOffice，原`PdfConverterService`只有LibreOffice路径，因此新生成和历史归档的PDF按需下载均失败。
- 修复：保留LibreOffice首选路径；Windows检测到Microsoft PowerPoint时，通过独立PowerShell COM进程和短临时文件名执行`SaveAs(..., 32)`原生PDF导出，兼容本机PowerPoint 12.0。转换日志移除emoji，避免重定向控制台使用`cp1252`时在转换前触发编码异常。
- 验证：`test_pdf_converter.py`覆盖PowerPoint可用性、回退路由和无转换器错误；相关转换、CV文件名、归档与下载权限测试通过。真实归档PPTX经Python服务导出PDF成功，文件150131字节且文件头为`%PDF-`。未安装额外运行时依赖。

### 2026-11-05 CV PDF 下载修复

- 根因：CV 归档旧逻辑只稳定记录 PPTX，且 PDF 依赖 LibreOffice；登录用户下载走归档接口时，历史记录即使有 PPTX 也没有 PDF 操作或文件记录。
- 修复：新任务保存并归档 PDF 路径；旧记录下载 PDF 时从归档 PPTX 按需转换并写回资源文件；CV 库对只有 PPTX 的历史记录仍显示 PDF 操作。转换器不可用时返回明确环境错误，不伪造可下载状态。
- 验证：访问控制、输出名称、PPTX 完整性回归共 14 项通过，Python 编译检查通过；当前 Windows 开发环境未安装 LibreOffice（`is_available=False`），无法在本机完成真实 PDF 转换。部署镜像已包含 `libreoffice` 与 `libreoffice-impress`。
