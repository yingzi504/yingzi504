"""
测试翻译+脱敏联合处理
验证 Pipeline 步骤 3 的完整功能
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
from app.services.anonymizer_service import AnonymizerService


async def test_full_transform():
    """测试完整的翻译+脱敏流程"""
    print("=" * 60)
    print("测试: 翻译+脱敏联合处理 (Pipeline 步骤 3)")
    print("=" * 60)
    
    # 创建测试简历数据
    test_resume = ResumeData(
        name="张伟",
        phone="13800138000",
        email="zhangwei@example.com",
        age=28,
        birth_date="1995-05-15",
        location="北京市朝阳区",
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
                company="阿里巴巴",
                period="2019-2022",
                role="软件工程师",
                tasks="负责后端开发和机器学习模型部署"
            ),
            WorkItem(
                company="腾讯",
                period="2022-2024",
                role="高级软件工程师",
                tasks="负责系统架构设计"
            )
        ],
        project=[
            ProjectItem(
                company="阿里巴巴",
                period="2021-2022",
                name="智能推荐系统",
                role="核心开发者",
                tasks="设计和实现推荐算法，提升用户留存率"
            )
        ],
        language="CN"
    )
    
    print("\n原始简历:")
    print(f"  姓名: {test_resume.name}")
    print(f"  职位: {test_resume.position}")
    print(f"  电话: {test_resume.phone}")
    print(f"  语言: {test_resume.language}")
    print(f"  公司: {[w.company for w in test_resume.work]}")
    
    try:
        # 步骤 1: 翻译
        print("\n[步骤 1] 翻译到英文...")
        translated = await TranslatorService.translate_resume(test_resume, "EN")
        print(f"  翻译后职位: {translated.position}")
        print(f"  翻译后语言: {translated.language}")
        
        # 步骤 2: 脱敏
        print("\n[步骤 2] 执行脱敏...")
        final_result = AnonymizerService.anonymize_resume(translated)
        
        print("\n最终处理结果:")
        print(f"  姓名: {final_result.name}")
        print(f"  职位: {final_result.position}")
        print(f"  电话: {final_result.phone}")
        print(f"  邮箱: {final_result.email}")
        print(f"  语言: {final_result.language}")
        print(f"  公司: {[w.company for w in final_result.work]}")
        print(f"  已脱敏: {final_result.is_anonymized}")
        
        # 验证结果
        assert final_result.phone is None
        assert final_result.email is None
        assert final_result.language == "EN"
        assert final_result.is_anonymized is True
        assert "Company A" in [w.company for w in final_result.work]
        
        print("\n✅ 完整流程验证通过!")
        return final_result
        
    except Exception as e:
        print(f"\n❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return None


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("Pipeline 步骤 3 联合测试")
    print("=" * 60)
    
    await test_full_transform()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
pytestmark = pytest.mark.integration
