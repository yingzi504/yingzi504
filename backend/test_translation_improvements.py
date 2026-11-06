"""
测试翻译改进
"""
import sys
import os
from pathlib import Path
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.schemas.resume import (
    ResumeData, WorkItem, ProjectItem, EducationItem,
    TranslationRequest, TransformRequest
)
from app.services.translator_service import TranslatorService


async def test_translation_quality():
    """测试翻译质量改进"""
    print("=" * 80)
    print("  测试翻译改进")
    print("=" * 80)
    
    # 创建测试简历数据 - 包含混合语言的情况
    test_resume = ResumeData(
        name="张伟",
        position="汽车动力系统工程师",
        technical_area="新能源汽车 / 动力电池",
        total_exp="8年",
        summary="具有8年汽车行业经验，专注于动力系统开发和新能源技术。",
        tech_skills="MATLAB, Simulink, AutoCAD, CATIA, ANSYS",
        lang_skills="英语（流利）, 日语（基础）",
        lang_skills_level="流利",
        training_exp="汽车动力系统培训, 新能源技术认证",
        education=[
            EducationItem(
                period="2012-2016",
                school="清华大学",
                degree="学士",
                major="车辆工程"
            )
        ],
        work=[
            WorkItem(
                company="某汽车公司",
                period="2016-2020",
                role="汽车动力系统工程师",
                tasks="""1. Responsible for the EDS parameter calculation.
2. Responsible for the technical item confirm according to the vehicle request.
3. Responsible for the EDS performance test data analysis.
4. Responsible for the EDS trouble shooting."""
            ),
            WorkItem(
                company="某新能源公司",
                period="2020-2024",
                role="高级系统工程师",
                tasks="负责动力电池系统设计与优化，参与多个新能源车型开发项目。"
            )
        ],
        project=[
            ProjectItem(
                company="某汽车公司",
                period="2018-2020",
                name="纯电动SUV开发项目",
                role="核心工程师",
                tasks="负责动力系统匹配与性能验证，达成续航里程目标。"
            )
        ],
        language="CN",
        is_anonymized=False
    )
    
    print("\n[测试 1] 中译英 - 测试混合语言内容的完整翻译...")
    try:
        translated = await TranslatorService.translate_resume(test_resume, "EN")
        print(f"  ✓ 翻译成功")
        print(f"  ✓ 原职位: {test_resume.position}")
        print(f"  ✓ 翻译后: {translated.position}")
        print(f"  ✓ 原工作经历示例:")
        print(f"    {test_resume.work[0].tasks[:100]}...")
        print(f"  ✓ 翻译后:")
        print(f"    {translated.work[0].tasks[:100]}...")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[测试 2] 英译中 - 验证反向翻译...")
    try:
        # 创建英文简历
        en_resume = ResumeData(
            name="Zhang Wei",
            position="Automotive Powertrain Engineer",
            technical_area="New Energy Vehicles / Power Battery",
            total_exp="8 years",
            language="EN"
        )
        translated_cn = await TranslatorService.translate_resume(en_resume, "CN")
        print(f"  ✓ 翻译成功")
        print(f"  ✓ 原职位: {en_resume.position}")
        print(f"  ✓ 翻译后: {translated_cn.position}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    
    print("\n[测试 3] 使用 TransformRequest 并测试 template_language...")
    try:
        transform_req = TransformRequest(
            resume_data=test_resume,
            template_language="EN",  # 模板语言为英文，自动翻译为英文
            perform_anonymization=False
        )
        # 这里直接调用翻译服务来模拟
        from app.api.resume import transform_resume
        # 注意：在测试中我们直接调用服务
        result = await TranslatorService.translate_resume(
            transform_req.resume_data, 
            transform_req.template_language
        )
        print(f"  ✓ 成功")
        print(f"  ✓ 模板语言: {transform_req.template_language}")
        print(f"  ✓ 结果语言: {result.language}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    
    print("\n" + "=" * 80)
    print("测试完成！")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_translation_quality())
