"""
验证测试：步骤2.5 - LLM结构化抽取服务（Pipeline 步骤 2）
"""
import sys
import os
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
import pytest
from app.services.extractor_service import ExtractorService
from app.schemas.resume import ResumeData


async def run_extractor_demo():
    """测试信息抽取服务"""
    print("=" * 60)
    print("验证测试：步骤2.5 - LLM结构化抽取服务")
    print("=" * 60)
    
    test_cases = [
        {
            "name": "1. 测试完整简历信息抽取",
            "func": test_complete_resume_extraction
        },
        {
            "name": "2. 测试边界情况（信息缺失）",
            "func": test_partial_resume_extraction
        },
        {
            "name": "3. 测试返回数据结构完整性",
            "func": test_data_structure_validation
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 60)
        try:
            await test["func"]()
            print("✓ 测试通过")
            passed += 1
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            import traceback
            traceback.print_exc()
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


@pytest.mark.integration
async def test_complete_resume_extraction():
    """测试完整简历信息抽取"""
    sample_resume = """
张伟
电话: 13800138000
邮箱: zhangwei@example.com
所在地: 北京
年龄: 32岁
出生日期: 1994-05-15

求职意向: 高级软件工程师
技术领域: 后端开发

教育经历:
2012.09 - 2016.07  清华大学  计算机科学与技术  本科
2016.09 - 2019.07  北京大学  软件工程  硕士

工作经历:
2019.07 - 2022.08  阿里巴巴  软件工程师
负责电商平台后端开发，参与订单系统设计，优化数据库查询性能，提升系统响应速度50%

2022.09 - 至今  字节跳动  高级软件工程师
主导推荐系统后端架构设计，带领5人团队完成多个核心功能迭代，系统日活用户提升30%

项目经历:
2020.03 - 2021.06  阿里巴巴  双十一订单系统重构  核心开发
负责订单创建和查询模块重构，使用Redis缓存优化热点数据，系统承载能力提升200%

技术技能: Python, Java, Go, MySQL, Redis, Kafka, Docker, Kubernetes
语言技能: 英语  流利
培训经历: AWS认证解决方案架构师

个人简介: 8年后端开发经验，精通分布式系统设计，善于解决复杂技术问题，具有良好的团队协作能力
"""
    
    resume_data = await ExtractorService.extract_structure(sample_resume)
    
    assert isinstance(resume_data, ResumeData), "返回类型应为ResumeData"
    assert resume_data.name is not None, "姓名不应为空"
    assert len(resume_data.education) > 0, "教育经历不应为空"
    assert len(resume_data.work) > 0, "工作经历不应为空"
    
    print(f"  ✓ 抽取到姓名: {resume_data.name}")
    print(f"  ✓ 教育经历数量: {len(resume_data.education)}")
    print(f"  ✓ 工作经历数量: {len(resume_data.work)}")
    print(f"  ✓ 技术技能: {resume_data.tech_skills[:30]}...")


@pytest.mark.integration
async def test_partial_resume_extraction():
    """测试信息缺失的边界情况"""
    partial_resume = """
李明
求职意向: 产品经理

工作经历:
2020.01 - 至今  腾讯  产品经理
负责产品规划和需求分析
"""
    
    resume_data = await ExtractorService.extract_structure(partial_resume)
    
    assert isinstance(resume_data, ResumeData), "返回类型应为ResumeData"
    # 允许部分字段为空
    assert resume_data.name is not None, "姓名应能抽取到"
    
    print(f"  ✓ 成功处理信息缺失的简历")
    print(f"  ✓ 抽取到姓名: {resume_data.name}")


async def test_data_structure_validation():
    """测试返回数据结构完整性"""
    resume_data = ResumeData()
    
    # 验证所有字段都存在（即使为空）
    required_fields = [
        'name', 'phone', 'email', 'location', 'age', 'birth_date',
        'position', 'technical_area', 'total_exp',
        'education', 'work', 'project',
        'tech_skills', 'lang_skills', 'lang_skills_level', 'training_exp',
        'summary', 'language'
    ]
    
    for field in required_fields:
        assert hasattr(resume_data, field), f"缺少字段: {field}"
    
    print("  ✓ 所有必需字段都存在")
    print("  ✓ ResumeData结构完整")


if __name__ == "__main__":
    success = asyncio.run(run_extractor_demo())
    sys.exit(0 if success else 1)
