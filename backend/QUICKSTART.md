 # 快速开始 - AI简历模板转换工具测试

## 🚀 三步开始测试

### 第一步：环境配置和启动后端服务

**首次使用需要创建conda环境：**

```bash
cd d:\ai_resume\backend
conda create -n ai_resume python=3.9
conda activate ai_resume
pip install -r requirements.txt
```

**启动服务：**

```bash
cd d:\ai_resume\backend
conda activate ai_resume
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

看到 `Uvicorn running on http://0.0.0.0:8000` 就说明服务启动成功了！

### 第二步：运行演示脚本（先用这个测试）

打开另一个终端，执行：

```bash
cd d:\ai_resume\backend
conda activate ai_resume
python tests\test_complete_pipeline.py
```

这个脚本会使用模拟数据演示完整流程！

### 第三步：用你的真实简历测试

#### 方法A：通过浏览器（推荐新手）
1. 打开浏览器访问：http://localhost:8000/docs
2. 找到 `/api/v1/resume/upload-and-parse` 接口
3. 点击 "Try it out" → 上传你的简历
4. 按照页面提示一步步操作

#### 方法B：按顺序手动调用（适合想了解细节）

1. **上传并解析简历**
   - 接口：`POST /api/v1/resume/upload-and-parse`
   - 输入：你的简历文件（PDF/Word）
   - 输出：解析后的文本

2. **结构化抽取**
   - 接口：`POST /api/v1/resume/extract`
   - 输入：上面的文本内容
   - 输出：结构化的ResumeData

3. **翻译+脱敏**
   - 接口：`POST /api/v1/resume/transform`
   - 输入：ResumeData，选择目标语言
   - 输出：翻译并脱敏后的简历

4. **摘要优化**
   - 接口：`POST /api/v1/resume/summarize`
   - 输入：处理后的ResumeData
   - 输出：优化后的简历

5. **填充PPT**
   - 接口：`POST /api/v1/resume/fill`
   - 输入：最终的ResumeData
   - 输出：生成的PPT文件名

6. **下载PPT**
   - 接口：`GET /api/v1/resume/fill/download/{filename}`
   - 输入：上面返回的文件名
   - 输出：下载你的PPT简历！

## 📂 重要目录说明

```
d:\ai_resume\backend\
├── templates\    # 放PPT模板的地方
├── uploads\      # 上传的简历存在这里
├── output\       # 生成的PPT存在这里
├── tests\        # 测试脚本
└── app\          # 后端代码
```

## ⚠️ 常见问题

**Q: 端口8000被占用怎么办？**
```bash
# 修改端口启动
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8080
```

**Q: 提示缺少依赖？**
```bash
pip install -r requirements.txt
```

**Q: PPT模板在哪里？**
检查 `d:\ai_resume\backend\templates\` 目录，确保有PPT模板文件。

## 📞 需要帮助？

1. 先看 `TEST_GUIDE.md` - 详细测试指南
2. 看 `memory-bank/` 下的文档 - 了解系统设计
3. 检查终端的错误信息 - 根据提示修复

---

## 🎉 祝你测试顺利！

有任何问题随时反馈！
