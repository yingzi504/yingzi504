# 翻译残留问题整改任务清单

## 1. 任务目标

解决简历中英文互译后仍残留源语言内容的问题，尤其是：

- 英文模板中出现中文职责段落、职位或字段。
- 中文模板中残留英文短词、姓名、缩写或职位。
- LLM 翻译失败后结果仍被当作成功结果送入摘要和 PPT 填充。
- 摘要、岗位字段或 Pipeline 后处理重新写入源语言内容。

最终要求：进入 PPT 填充阶段的 `ResumeData` 必须通过目标语言审查；无法满足时任务应失败并返回可定位的字段问题，而不是静默生成部分翻译结果。

## 2. 相关文件与约束

### 核心实现

- `backend/app/services/translator_service.py`
- `backend/app/services/translator_service_old.py`
- `backend/app/services/pipeline_service.py`
- `backend/app/api/resume.py`
- `backend/app/schemas/resume.py`

### 参考文档

- `memory-bank/architecture.md`
  - 翻译服务职责：批量翻译 `ResumeData` 的所有文本字段。
  - 流程：检测源语言 -> 逐字段翻译 -> 重组 `ResumeData`。
  - 翻译结果随后进入摘要和 PPT 填充。
- `memory-bank/design-document.md`
  - 翻译+脱敏属于 P0 流程。
  - 经历内容必须完整保留，不能因翻译或摘要遗漏职责条目。
- `backend/docs/TRANSLATION_IMPROVEMENTS.md`
  - `template_language` 优先于 `target_language`。
  - 目标语言只允许 `CN` 或 `EN`，不区分大小写。

### 当前已知问题定位

- `translator_service.py:394-413`：3 次残留重试后仍返回最后结果。
- `translator_service.py:171-197`：二次审查最多两轮，结束时不强制校验通过。
- `translator_service.py:125-148`：翻译审查字段注册表不完整。
- `translator_service.py:92-100`：短英文 token 可能漏检。
- `translator_service.py:332-405`：技术术语策略没有贯穿初次翻译和结果校验。
- `translator_service.py:205-217`：编号职责列表不会拆分。
- `translator_service.py:309-313`：结果清理规则可能删除正文。
- `pipeline_service.py:380-400`：最终审查后重新写入 `technical_area` 和岗位字段。
- `api/resume.py:249-254`：目标语言未统一规范化和校验。
- `translator_service_old.py`：无活动引用，且行为落后于新实现。

## 3. 执行原则

- 默认只修改与翻译质量、字段完整性和 Pipeline 契约直接相关的代码。
- 不使用硬编码字符串替换来“伪修复”整段翻译残留。
- LLM 输出必须经过确定性的结构校验和语言审查。
- 任何 fallback 都必须满足目标语言契约；不能把源语言文本静默作为成功结果。
- 保留原始 `ResumeData`，翻译过程使用深拷贝，失败时不污染输入对象。
- 每完成一个阶段都增加或更新回归测试，再进入下一阶段。

## 4. P1 实施清单

### P1-1 阻止未通过审查的译文进入 PPT

- [x] 定义统一异常，例如 `TranslationQualityError`，包含：
  - `target_language`
  - 未通过的字段路径列表
  - 每个字段的检测原因
  - 最后一次模型输出是否可用
- [x] 修改 `translate_text()`：
  - 连续重试后仍含源语言时抛出质量异常，或返回显式失败对象。
  - 不允许直接返回最后一次残留字符串。
  - 空模型输出与残留模型输出分开处理。
- [x] 修改 `review_and_retranslate()`：
  - 完成重译后执行最终 `audit_translation()`。
  - 仍有问题时抛出异常，不返回“看起来成功”的 `ResumeData`。
  - 保留字段路径，便于 API 和任务状态展示。
- [x] 修改 Pipeline：
  - 翻译质量异常必须让任务进入 failed 状态。
  - 不调用摘要、PPT 填充和下载生成。
  - 日志中记录字段路径，不记录完整简历隐私内容。
- [x] 增加测试：LLM 连续返回混合语言时，翻译接口失败且不生成 PPT。

### P1-2 统一目标语言入口契约

- [x] 增加 `normalize_target_language(value)`：
  - `strip()`。
  - `upper()`。
  - 只接受 `CN`、`EN`。
  - 空值和其他值返回明确的 400 错误。
- [x] 在 `api/resume.py:_resolve_target_language()` 使用该函数。
- [x] 在 `TranslatorService.translate_resume()` 和 `translate_text()` 再做一次边界校验，避免内部调用绕过 API。
- [x] 确保 `template_language` 优先于 `target_language`，但两者都要校验。
- [x] 增加测试：`en`、` EN ` 能正常工作；`FR`、空字符串、未知值必须失败。

### P1-3 建立完整且唯一的翻译字段注册表

- [x] 以 `ResumeData` schema 为基准，列出所有需要翻译的文本字段。
- [x] 至少覆盖：
  - `name`
  - `position`
  - `technical_area`
  - `location`
  - `birth_date`（若脱敏前直接翻译接口允许该字段存在）
  - `total_exp`
  - `summary`
  - `tech_skills`
  - `lang_skills`
  - `lang_skills_level`
  - `training_exp`
  - `job_position`
  - `job_position_en`
  - 教育、工作、项目中的所有文本字段
- [x] 明确不翻译字段：电话、邮箱、年龄、布尔值、语言元数据等。
- [x] 对 `anonymized_name`、`anonymized_name_cn` 写出明确规则，避免被翻译流程覆盖脱敏结果。
- [x] 初次翻译、二次审查和最终审查必须复用同一个字段注册表。
- [x] 增加测试：每个字段注入源语言内容，确认均会被翻译或按规则明确排除。

### P1-4 修复残留检测器

- [x] 将 `_has_language_residue()` 改为字段感知的检测策略，而不是单一全局正则。
- [x] 目标英文：检测中文字符，必要时扩展日文、韩文字符集。
- [x] 目标中文：检测英文单词、短 token、姓名和职位缩写。
- [x] 覆盖长度为 1-2 的 token：`AI`、`PM`、`Li`、`Wu` 等。
- [x] 对 `C++`、`R&D`、`ISO-26262` 等模式做明确分类，不因正则漏检而误判为已翻译。
- [x] 技术术语只允许来自显式术语表或严格的技术标识符规则。
- [x] 不允许“全部大写”成为无限制豁免条件；`RESPONSIBLE` 等普通英文不能被自动放行。
- [x] 增加测试矩阵：
  - `AI`、`PM`、`Li`、`Wu`。
  - `Python`、`Linux`、`CANoe`、`ADAS`。
  - 普通英文职位词。
  - 中英混合句子。

### P1-5 统一技术术语策略

- [x] 给 `translate_text()` 增加字段策略参数，例如 `allow_technical` 或更明确的 `field_policy`。
- [x] 初次跳过判断、LLM 输出判断、`audit_translation()` 使用同一策略。
- [x] 目标中文的技术名词按术语表保留，不触发无效的 3 次重试。
- [x] 目标中文的普通英文技能名称仍需翻译，不能因为字段整体是 `tech_skills` 就全部放行。
- [x] 读取 `data/term_base.json`，将术语映射注入 prompt 或结构化处理。
- [x] 删除或实现未使用的 `LANG_SKILLS_WORDS`，避免产生未兑现的功能假设。

### P1-6 保证职责条目不丢失

- [x] 扩展 `_task_items()`，支持：
  - `1. ...`、`2) ...`、`(3) ...`。
  - `-`、`*`、`•` 等项目符号。
  - 中英文分号和换行。
- [x] 翻译前记录输入条数，翻译后校验输出条数。
- [x] 优先使用 JSON 数组逐项翻译，避免一整个长段落交给单次 LLM 调用。
- [x] 某一项翻译失败时只回退该项，并将字段标记为质量问题；不能静默丢弃。
- [x] 增加长职责列表测试，确认每一项均存在且顺序不变。

### P1-7 修复 Pipeline 的最终写入顺序

- [x] `technical_area`、`job_position`、`job_position_en` 等派生字段全部写入后，再执行最终翻译审查。
- [x] `_resolve_target_technical_area()` 失败时不得直接返回不符合目标语言的源文本。
- [x] 中文目标岗位写入英文简历前必须得到合法英文结果，否则任务失败或要求人工确认。
- [x] 最终审查后不得再有任何会写入简历文本字段的步骤。
- [x] 增加 Pipeline 集成测试，覆盖岗位翻译失败和技术领域回退场景。

## 5. P2 实施清单

### P2-1 收紧模型输出清理

- [x] `_clean_translation_result()` 只删除明确的 Markdown 包装和精确标题。
- [x] 不使用 `.*lang.*skill.*` 这种宽泛匹配删除整行正文。
- [x] 增加正文包含“Language skills”或“语言技能”的测试，确认正文不会被删除。

### P2-2 处理旧实现

- [x] 再次确认全仓库没有 `translator_service_old` 的导入。
- [x] 确认部署脚本、历史任务和外部入口不依赖旧模块。
- [x] 删除 `translator_service_old.py`，或移动到明确的 archived 目录并禁止生产导入。
- [x] 删除后运行全仓库导入检查和测试。

### P2-3 统一日志和错误响应

- [x] 使用项目日志组件替代 `print()`。
- [x] 日志记录字段路径、重试次数和错误类型，不记录完整简历文本。
- [x] 将翻译质量失败映射到统一 API 错误码，例如 `TRANSLATION_QUALITY_ERROR`。
- [x] 响应中提供可读的字段路径，例如 `work[0].tasks`。

## 6. 推荐实施顺序

1. 先完成 P1-1，确保残留不会继续生成 PPT。
2. 完成 P1-2，锁定 `CN/EN` 入口契约。
3. 完成 P1-3，建立完整字段注册表。
4. 完成 P1-4 和 P1-5，统一残留检测和术语策略。
5. 完成 P1-6，修复长职责列表的内容丢失风险。
6. 完成 P1-7，确保 Pipeline 最终写入后仍通过审查。
7. 完成 P2 清理和结构性改进。
8. 最后运行完整回归测试，并用真实中英文简历各抽样验证。

## 7. 验收标准

### 功能验收

- [ ] 中文简历 -> 英文模板：所有正文、职位、项目、教育、技能字段无中文残留。
- [ ] 英文简历 -> 中文模板：普通英文内容无残留；允许保留的技术术语有明确记录。
- [x] 元数据标错语言但字段实际为混合语言时，仍能检测并修复。
- [x] 目标语言为小写或带空格时行为正确。
- [x] 非 `CN/EN` 目标语言被拒绝。
- [x] LLM 连续返回残留时任务失败，不产生成功 PPT。
- [x] 长职责列表的条目数量、顺序和关键信息保持一致。
- [x] 摘要和岗位字段后处理不会重新引入源语言。

### 质量验收

- [x] 所有翻译字段都有单元测试。
- [x] 有至少一个 LLM mock 测试验证“第一次混合、第二次通过”。
- [x] 有至少一个测试验证“三次均失败必须失败闭环”。
- [x] 有字段审查遗漏检测测试，新增 `ResumeData` 文本字段时测试会提醒更新注册表。
- [x] 有 Pipeline 集成测试验证最终审查位于最后一次字段写入之后。
- [x] 运行 `python -m py_compile` 检查所有修改的 Python 文件。
- [x] 在安装 `pytest` 的环境运行后端完整测试集。

## 8. 建议测试用例矩阵

| 场景 | 目标 | 关键断言 |
|---|---|---|
| 纯中文简历 -> EN | 基本翻译 | 所有文本字段无中文字符 |
| 纯英文简历 -> CN | 反向翻译 | 普通英文词不残留 |
| 中英混合职责 | 残留修复 | 混合句经过重译并通过最终 audit |
| 元数据为 CN、字段为英文 | 源语言推断 | 不因 metadata 错误而跳过翻译 |
| `AI`/`PM`/`Li`/`Wu` | 短 token | 不能被残留检测器漏掉 |
| `Python`/`Linux`/`CANoe` | 技术术语 | 按术语策略保留且不触发无效重试 |
| 编号职责列表 | 内容完整性 | 输入输出条目数一致 |
| 日期 `2021-03 至今` | 格式统一 | 输出符合 `YYYY.MM - Present/至今` |
| 缺失或非法目标语言 | 输入校验 | 返回 400/统一错误码 |
| LLM 三次均返回残留 | 失败闭环 | 不返回成功数据、不填充 PPT |
| 岗位翻译 fallback | Pipeline 顺序 | 最终 audit 能拦截源语言回退 |

## 9. 新对话启动说明

在新的对话框中可直接发送以下内容：

> 请继续执行 `docs/translation-residue-remediation-checklist.md`。先检查当前 git 状态和已完成项，按“推荐实施顺序”从第一个未完成的 P1 任务开始。每完成一个任务就更新清单、增加对应测试并运行验证。不要直接删除用户已有改动；若 pytest 不可用，先说明并至少运行 `py_compile` 和可执行的本地回归探针。

## 10. 完成记录

- [x] P1-1：阻止未通过审查的译文进入 PPT
- [x] P1-2：统一目标语言入口契约
- [x] P1-3：完整翻译字段注册表
- [x] P1-4：残留检测器
- [x] P1-5：技术术语策略
- [x] P1-6：职责条目完整性
- [x] P1-7：Pipeline 最终写入顺序
- [x] P2-1：模型输出清理
- [x] P2-2：旧实现处理
- [x] P2-3：日志和错误响应

## 11. 验证记录（2026-09-04）

- [x] 所有本轮修改和新增的 Python 文件通过 `python -m py_compile`。
- [x] 标准库 unittest 回归共 37 项通过：翻译 25 项、语言契约 7 项、Pipeline 4 项、旧模块守卫 1 项。
- [x] 既有本地可执行回归探针 5 项通过，包括目标岗位技术领域、混合语言重试、元数据误标和职责完整性。
- [x] pytest 默认回归套件通过：127 项通过、9 项显式集成测试按标记排除、60 项 subtests 通过。

## 12. 验证记录（2026-09-07）

- [x] 已安装 `pytest 9.1.1` 和 `pytest-asyncio 1.4.0`，异步测试使用 auto 模式。
- [x] 修复测试收集错误、过时接口测试和实际代码回归后，默认套件无 failed/error。
- [x] Web 后端的 `app.*` logger 输出到启动终端；pytest 也实时展示 INFO 及以上日志。
