"""
完整Pipeline测试脚本
测试从简历上传→解析→抽取→翻译→脱敏→摘要→填充的完整流程
"""
import asyncio
import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.resume import (
    ResumeData, WorkItem, ProjectItem, EducationItem,
    ExtractionRequest, ExtractionResponse,
    TransformRequest, TransformResponse,
    SummarizationRequest, SummarizationResponse,
    FillerRequest, FillerResponse
)
from app.services.parser_service import ParserService
from app.services.extractor_service import ExtractorService
from app.services.translator_service import TranslatorService
from app.services.anonymizer_service import AnonymizerService
from app.services.summarization_service import SummarizationService
from app.services.filler_service import FillerService
from app.services.template_config import TemplateType


async def test_complete_pipeline_demo():
    """
    演示完整Pipeline流程（使用模拟数据）
    不需要实际文件，直接使用演示数据测试所有服务
    """
    print("=" * 80)
    print("  AI简历模板转换工具 - 完整Pipeline演示")
    print("=" * 80)
    
    # 步骤1：创建模拟简历数据（模拟解析和抽取后的结果）
    print("\n" + "=" * 80)
    print("  [步骤1 & 2] 模拟文档解析和LLM结构化抽取")
    print("=" * 80)
    
    demo_resume = ResumeData(
        name="张伟",
        phone="13800138000",
        email="zhangwei@example.com",
        location="北京市朝阳区",
        age=28,
        birth_date="1995-05-15",
        position="Python开发工程师",
        technical_area="人工智能/机器学习",
        total_exp="5年",
        summary="""我在过去5年中一直从事Python开发工作，主要涉及机器学习和数据分析方向。参与过多个大型项目的开发和设计，积累了丰富的实战经验。""",
        tech_skills="Python, TensorFlow, PyTorch, Scikit-learn, SQL, Docker, Git",
        lang_skills="英语, 日语",
        lang_skills_level="流利",
        training_exp="机器学习工程师认证",
        education=[
            EducationItem(
                period="2015-2019",
                school="清华大学",
                degree="学士",
                major="计算机科学与技术"
            )
        ],
        work=[
            WorkItem(
                company="科技有限公司",
                period="2019-2022",
                role="软件工程师",
                tasks="负责后端服务开发，参与机器学习模型的部署工作。负责系统架构设计和优化。我还做了一些项目管理相关工作。"
            ),
            WorkItem(
                company="创新科技集团",
                period="2022-2024",
                role="高级软件工程师",
                tasks="负责核心系统开发，带领团队完成项目。协调资源，推进项目进度。负责系统架构设计。"
            )
        ],
        project=[
            ProjectItem(
                company="科技有限公司",
                period="2021-2022",
                name="智能推荐系统",
                role="核心开发者",
                tasks="设计和实现推荐算法，优化用户体验。提升用户留存率20%。"
            ),
            ProjectItem(
                company="创新科技集团",
                period="2023-2024",
                name="数据分析平台",
                role="技术负责人",
                tasks="负责平台架构设计，核心模块开发。"
            )
        ],
        language="CN",
        is_anonymized=False
    )
    
    print("  ✓ 模拟数据创建成功")
    print(f"    姓名: {demo_resume.name}")
    print(f"    职位: {demo_resume.position}")
    print(f"    工作经历: {len(demo_resume.work)} 条")
    print(f"    项目经历: {len(demo_resume.project)} 条")
    
    # 步骤3：翻译+脱敏
    print("\n" + "=" * 80)
    print("  [步骤3] 翻译+脱敏")
    print("=" * 80)
    
    print("\n  [3.1] 翻译为英文...")
    try:
        translated = await TranslatorService.translate_resume(demo_resume, "EN")
        print("  ✓ 翻译成功")
        print(f"    职位: {translated.position}")
        print(f"    语言: {translated.language}")
    except Exception as e:
        print(f"  ✗ 翻译失败: {e}")
        translated = demo_resume
    
    print("\n  [3.2] 脱敏处理...")
    try:
        anonymized = AnonymizerService.anonymize_resume(translated)
        print("  ✓ 脱敏成功")
        print(f"    姓名: {anonymized.name}")
        print(f"    电话: {anonymized.phone}")
        print(f"    公司: {[w.company for w in anonymized.work]}")
        print(f"    已脱敏: {anonymized.is_anonymized}")
    except Exception as e:
        print(f"  ✗ 脱敏失败: {e}")
        anonymized = translated
    
    # 步骤4：约束性摘要
    print("\n" + "=" * 80)
    print("  [步骤4] 约束性摘要")
    print("=" * 80)
    
    print("\n  优化简历经历...")
    try:
        summarized = await SummarizationService.summarize_resume(anonymized)
        print("  ✓ 摘要优化成功")
        print(f"    个人简介: {summarized.summary[:50]}...")
        print(f"    工作经历[0]: {summarized.work[0].tasks[:50]}...")
    except Exception as e:
        print(f"  ✗ 摘要失败: {e}")
        summarized = anonymized
    
    # 步骤6：PPT模板填充
    print("\n" + "=" * 80)
    print("  [步骤6] PPT模板填充")
    print("=" * 80)
    
    print("\n  填充PPT模板...")
    try:
        output_path = await FillerService.fill_template(
            summarized,
            template_type=TemplateType.VERTICAL
        )
        print("  ✓ PPT填充成功！")
        print(f"    输出文件: {output_path}")
        print(f"    文件存在: {os.path.exists(output_path)}")
        
        print("\n" + "=" * 80)
        print("  🎉 完整Pipeline演示完成！")
        print("=" * 80)
        print(f"\n  输出文件: {output_path}")
        print("\n  下一步：")
        print("  1. 检查输出目录下的PPT文件")
        print("  2. 如果有实际简历，使用Swagger UI进行完整测试")
        print("  3. 参考 TEST_GUIDE.md 了解更多测试方法")
        
    except Exception as e:
        print(f"  ✗ PPT填充失败: {e}")
        import traceback
        traceback.print_exc()


async def main():
    """主函数"""
    await test_complete_pipeline_demo()


if __name__ == "__main__":
    asyncio.run(main())
pytestmark = pytest.mark.integration
