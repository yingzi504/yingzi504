"""
测试修复翻译问题
1. "9年" 单位未完全翻译
2. "English" 错误翻译为中文
"""
import sys
import os
from pathlib import Path
import asyncio

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.translator_service import TranslatorService


async def test_translation_issues():
    """测试特定翻译问题"""
    print("=" * 80)
    print("  测试翻译问题修复")
    print("=" * 80)
    
    print("\n[测试 1] 单位翻译 - '9年' 应完整翻译为 '9 years'...")
    
    # 测试语言检测功能
    test_cases = [
        ("9年", "CN"),
        ("9 years", "EN"),
        ("English", "EN"),
        ("中文", "CN"),
        ("汽车动力系统工程师", "CN"),
        ("Automotive Engineer", "EN")
    ]
    
    print("\n语言检测测试：")
    for text, expected in test_cases:
        detected = TranslatorService._detect_language(text)
        status = "✓" if detected == expected else "✗"
        print(f"  {status} '{text}' -> 检测={detected}, 期望={expected}")
    
    # 测试单位翻译
    print("\n单位翻译测试：")
    unit_tests = [
        ("9年", "CN", "EN"),
        ("5年", "CN", "EN"),
        ("10 years", "EN", "CN")
    ]
    
    for text, source, target in unit_tests:
        result = TranslatorService._translate_units(text, source, target)
        print(f"  '{text}' -> '{result}'")
    
    # 创建测试简历1 - 中文转英文，包含"9年"
    print("\n\n[测试 2] 中文简历翻译为英文，测试'9年'...")
    resume_cn = ResumeData(
        name="张三",
        position="汽车动力系统工程师",
        technical_area="新能源汽车",
        total_exp="9年",
        lang_skills="英语, 日语",
        language="CN"
    )
    
    try:
        translated = await TranslatorService.translate_resume(resume_cn, "EN")
        print(f"  ✓ 翻译成功")
        print(f"  ✓ 原工作经验: {resume_cn.total_exp}")
        print(f"  ✓ 翻译后: {translated.total_exp}")
        print(f"  ✓ 原语言技能: {resume_cn.lang_skills}")
        print(f"  ✓ 翻译后: {translated.lang_skills}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 创建测试简历2 - 英文转中文，测试"English"不被错误翻译
    print("\n\n[测试 3] 英文简历翻译为中文，测试'English'...")
    resume_en = ResumeData(
        name="Zhang San",
        position="Automotive Engineer",
        technical_area="New Energy Vehicles",
        total_exp="9 years",
        lang_skills="English, Japanese",
        language="EN"
    )
    
    try:
        translated = await TranslatorService.translate_resume(resume_en, "CN")
        print(f"  ✓ 翻译成功")
        print(f"  ✓ 原工作经验: {resume_en.total_exp}")
        print(f"  ✓ 翻译后: {translated.total_exp}")
        print(f"  ✓ 原语言技能: {resume_en.lang_skills}")
        print(f"  ✓ 翻译后: {translated.lang_skills}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 创建测试简历3 - 模拟问题场景：简历标记为CN，但lang_skills是English
    print("\n\n[测试 4] 模拟问题场景 - 标记为CN但内容是英文...")
    resume_mixed = ResumeData(
        name="Zhang San",
        position="Engineer",
        total_exp="9年",
        lang_skills="English",  # 英文内容
        language="CN"  # 标记为中文
    )
    
    try:
        translated = await TranslatorService.translate_resume(resume_mixed, "EN")
        print(f"  ✓ 翻译成功")
        print(f"  ✓ 原标记语言: {resume_mixed.language}")
        print(f"  ✓ 目标语言: EN")
        print(f"  ✓ 原语言技能: {resume_mixed.lang_skills}")
        print(f"  ✓ 翻译后: {translated.lang_skills}")
        print(f"  ✓ (如果已是英文，应该保持不变)")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)


if __name__ == "__main__":
    asyncio.run(test_translation_issues())
