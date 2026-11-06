"""
测试翻译服务
验证 Pipeline 步骤 3 的翻译功能
"""
import asyncio
import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.translator_service import TranslatorService


async def test_translate_text():
    """测试单个文本翻译"""
    print("=" * 60)
    print("测试 1: 单个文本翻译")
    print("=" * 60)
    
    test_cases = [
        ("中文测试文本", "CN", "EN"),
        ("This is a test resume content.", "EN", "CN"),
        ("Python开发工程师，擅长机器学习和数据分析", "CN", "EN"),
    ]
    
    for text, source, target in test_cases:
        try:
            print(f"\n原文 ({source}): {text}")
            translated = await TranslatorService.translate_text(text, source, target)
            print(f"译文 ({target}): {translated}")
        except Exception as e:
            print(f"翻译失败: {e}")


async def test_translate_resume():
    """测试简历翻译"""
    print("\n" + "=" * 60)
    print("测试 2: 简历翻译")
    print("=" * 60)
    
    # 创建测试简历数据
    test_resume = ResumeData(
        name="张伟",
        position="Python开发工程师",
        technical_area="人工智能",
        total_exp="5年",
        summary="具有5年Python开发经验，擅长机器学习和数据分析，参与过多个大型项目。",
        tech_skills="Python, TensorFlow, PyTorch, SQL, Docker",
        lang_skills="英语, 日语",
        education=[
            EducationItem(
                period="2015-2019",
                school="清华大学",
                degree="学士",
                major="计算机科学"
            )
        ],
        work=[
            WorkItem(
                company="科技公司A",
                period="2019-2022",
                role="软件工程师",
                tasks="负责后端开发和机器学习模型部署"
            )
        ],
        project=[
            ProjectItem(
                company="科技公司A",
                period="2021-2022",
                name="智能推荐系统",
                role="核心开发者",
                tasks="设计和实现推荐算法，提升用户留存率"
            )
        ],
        language="CN"
    )
    
    print("\n原始简历（中文）:")
    print(f"  姓名: {test_resume.name}")
    print(f"  职位: {test_resume.position}")
    print(f"  领域: {test_resume.technical_area}")
    print(f"  简介: {test_resume.summary}")
    print(f"  技能: {test_resume.tech_skills}")
    
    try:
        translated = await TranslatorService.translate_resume(test_resume, "EN")
        print("\n翻译后简历（英文）:")
        print(f"  姓名: {translated.name}")
        print(f"  职位: {translated.position}")
        print(f"  领域: {translated.technical_area}")
        print(f"  简介: {translated.summary}")
        print(f"  技能: {translated.tech_skills}")
        print(f"  语言: {translated.language}")
        return translated
    except Exception as e:
        print(f"翻译失败: {e}")
        return None


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("翻译服务测试")
    print("=" * 60)
    
    await test_translate_text()
    translated_resume = await test_translate_resume()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
pytestmark = pytest.mark.integration
