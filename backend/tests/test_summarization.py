"""
测试约束性摘要服务
验证 Pipeline 步骤 4 的摘要优化功能
"""
import asyncio
import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.summarization_service import SummarizationService


async def test_summarize_text():
    """测试单个文本摘要"""
    print("=" * 60)
    print("测试 1: 单个文本摘要优化")
    print("=" * 60)
    
    # 测试用例 - 中文
    test_cases_cn = [
        """我在公司主要做一些后端开发的工作，还参与了一些机器学习模型的部署，还有做了一些系统架构的设计。工作期间，我也负责了一些项目的核心开发，做了很多事情。""",
        """我主要是负责项目管理相关的工作，和团队成员一起合作，还协调了很多资源，推动了项目的进展。""",
    ]
    
    print("\n--- 中文测试 ---")
    for text in test_cases_cn:
        try:
            print(f"\n原文: {text}")
            summarized = await SummarizationService.summarize_text(text, "CN")
            print(f"优化: {summarized}")
        except Exception as e:
            print(f"失败: {e}")
    
    # 测试用例 - 英文
    test_cases_en = [
        """I was working on backend development, also I did some ML model deployment, and system architecture design. During this time, I also was responsible for core development of some projects, and did many things.""",
        """I was mainly responsible for project management, working with team members, coordinating resources, and driving project progress.""",
    ]
    
    print("\n--- 英文测试 ---")
    for text in test_cases_en:
        try:
            print(f"\nOriginal: {text}")
            summarized = await SummarizationService.summarize_text(text, "EN")
            print(f"Optimized: {summarized}")
        except Exception as e:
            print(f"Failed: {e}")


async def test_summarize_resume():
    """测试完整简历摘要"""
    print("\n" + "=" * 60)
    print("测试 2: 完整简历摘要优化")
    print("=" * 60)
    
    # 创建测试简历
    test_resume = ResumeData(
        name="Mr./Ms. Zhang",
        position="Software Engineer",
        technical_area="AI/ML",
        total_exp="5 years",
        summary="""我具有5年的开发经验，主要从事Python开发，还参与过多个大型项目，做了很多事情。在这些项目中，我学到了很多东西，也获得了丰富的经验。""",
        tech_skills="Python, TensorFlow, PyTorch, SQL, Docker",
        education=[
            EducationItem(
                period="2015-2019",
                school="Tsinghua University",
                degree="Bachelor",
                major="Computer Science"
            )
        ],
        work=[
            WorkItem(
                company="Company A",
                period="2019-2022",
                role="Software Engineer",
                tasks="""我在公司主要做一些后端开发的工作，还参与了一些机器学习模型的部署。工作期间，我也负责了一些项目的核心开发，做了很多事情。"""
            ),
            WorkItem(
                company="Company B",
                period="2022-2024",
                role="Senior Software Engineer",
                tasks="""我主要是负责系统架构设计，还带领了团队做一些项目，协调了很多资源，推动了项目的进展。"""
            )
        ],
        project=[
            ProjectItem(
                company="Company A",
                period="2021-2022",
                name="Recommendation System",
                role="Core Developer",
                tasks="""我设计和实现了推荐算法，还做了一些优化工作，提升了用户留存率，效果很不错。"""
            )
        ],
        language="CN"
    )
    
    print("\n原始简历:")
    print(f"  Summary: {test_resume.summary}")
    print(f"  Work[0] Tasks: {test_resume.work[0].tasks}")
    print(f"  Work[1] Tasks: {test_resume.work[1].tasks}")
    print(f"  Project[0] Tasks: {test_resume.project[0].tasks}")
    
    try:
        summarized = await SummarizationService.summarize_resume(test_resume)
        print("\n优化后简历:")
        print(f"  Summary: {summarized.summary}")
        print(f"  Work[0] Tasks: {summarized.work[0].tasks}")
        print(f"  Work[1] Tasks: {summarized.work[1].tasks}")
        print(f"  Project[0] Tasks: {summarized.project[0].tasks}")
        return summarized
    except Exception as e:
        print(f"失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("约束性摘要服务测试（Pipeline 步骤 4）")
    print("=" * 60)
    
    await test_summarize_text()
    await test_summarize_resume()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
pytestmark = pytest.mark.integration
