# AI简历模板转换工具 - 测试指南

## 📋 测试前准备

### 1. 环境配置
首先确保已经安装了Python和依赖（统一使用conda环境）：

```bash
# 进入后端目录
cd d:\ai_resume\backend

# 使用conda创建环境（必须）
conda create -n ai_resume python=3.9
conda activate ai_resume

# 安装依赖
pip install -r requirements.txt
```

### 2. 准备测试文件

你需要准备：
- **一份简历**（PDF或Word格式）
- **PPT模板**（放在 `templates/` 目录下）

## 🚀 开始测试

### 方法一：使用FastAPI Swagger UI（推荐）

#### 步骤1：启动后端服务

```bash
cd d:\ai_resume\backend
conda activate ai_resume
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### 步骤2：访问Swagger文档

打开浏览器，访问：
```
http://localhost:8000/docs
```

#### 步骤3：按照Pipeline顺序进行测试

**Pipeline 步骤1：上传并解析简历**
1. 找到 `POST /api/v1/resume/upload-and-parse`
2. 点击 "Try it out"
3. 选择你的简历文件（PDF/Word/图片）
4. 点击 "Execute"
5. 保存返回的解析结果（text_content）

**Pipeline 步骤2：LLM结构化抽取**
1. 找到 `POST /api/v1/resume/extract`
2. 点击 "Try it out"
3. 将上一步的text_content填入raw_text字段
4. 点击 "Execute"
5. 保存返回的ResumeData

**Pipeline 步骤3：翻译+脱敏**
1. 找到 `POST /api/v1/resume/transform`
2. 点击 "Try it out"
3. 将上一步的ResumeData填入
4. 设置target_language（"EN"或"CN"）
5. 设置perform_anonymization: true
6. 点击 "Execute"

**Pipeline 步骤4：约束性摘要**
1. 找到 `POST /api/v1/resume/summarize`
2. 点击 "Try it out"
3. 将处理后的ResumeData填入
4. 点击 "Execute"

**Pipeline 步骤6：PPT模板填充**
1. 找到 `POST /api/v1/resume/fill`
2. 点击 "Try it out"
3. 将最终的ResumeData填入
4. 设置template_type（"vertical"或"horizontal"）
5. 点击 "Execute"
6. 保存返回的filename
7. 访问 `GET /api/v1/resume/fill/download/{filename}` 下载PPT

### 方法二：使用Python测试脚本（推荐）

我已经为你创建了一个完整的测试脚本！让我来创建它：
