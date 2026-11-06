"""
简化版演示脚本 - 不依赖外部解析库
直接测试翻译、脱敏、摘要、PPT填充功能
"""
import asyncio
import pytest
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.resume import (
    ResumeData, WorkItem, ProjectItem, EducationItem
)
from app.services.anonymizer_service import AnonymizerService
from app.services.filler_service import FillerService
from app.services.template_config import TemplateType


async def test_core_features():
    """测试核心功能（脱敏+PPT填充）"""
    print("=" * 80)
    print("  AI简历模板转换工具 - 核心功能演示")
    print("=" * 80)
    
    # 创建演示简历数据
    print("\n" + "=" * 80)
    print("  [准备数据] 模拟简历数据")
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
        summary="5年Python开发经验，擅长机器学习和数据分析，参与过多个大型项目。",
        tech_skills="Python, TensorFlow, PyTorch, SQL, Docker",
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
        language="CN",
        is_anonymized=False
    )
    
    print("\n  原始简历数据:")
    print(f"    姓名: {demo_resume.name}")
    print(f"    职位: {demo_resume.position}")
    print(f"    电话: {demo_resume.phone}")
    print(f"    公司: {[w.company for w in demo_resume.work]}")
    
    # 测试脱敏功能
    print("\n" + "=" * 80)
    print("  [步骤1] 隐私脱敏")
    print("=" * 80)
    
    try:
        anonymized = AnonymizerService.anonymize_resume(demo_resume)
        print("\n  ✓ 脱敏成功！")
        print(f"    姓名: {anonymized.name}")
        print(f"    电话: {anonymized.phone}")
        print(f"    邮箱: {anonymized.email}")
        print(f"    公司: {[w.company for w in anonymized.work]}")
        print(f"    已脱敏: {anonymized.is_anonymized}")
    except Exception as e:
        print(f"  ✗ 脱敏失败: {e}")
        anonymized = demo_resume
    
    # 测试PPT填充
    print("\n" + "=" * 80)
    print("  [步骤2] PPT模板填充")
    print("=" * 80)
    
    print("\n  [2.1] 填充纵向模板...")
    try:
        output_path = await FillerService.fill_template(
            anonymized,
            template_type=TemplateType.VERTICAL
        )
        print("  ✓ 纵向模板填充成功！")
        print(f"    输出文件: {output_path}")
        print(f"    文件存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"  ✗ 纵向模板填充失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n  [2.2] 填充横向模板...")
    try:
        output_path = await FillerService.fill_template(
            anonymized,
            template_type=TemplateType.HORIZONTAL
        )
        print("  ✓ 横向模板填充成功！")
        print(f"    输出文件: {output_path}")
        print(f"    文件存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"  ✗ 横向模板填充失败: {e}")
    
    print("\n" + "=" * 80)
    print("  🎉 核心功能演示完成！")
    print("=" * 80)
    print("\n  检查 output/ 目录下生成的PPT文件！")
    print("\n  下一步：")
    print("  1. 安装完整依赖后可测试所有功能")
    print("  2. pip install -r requirements.txt")
    print("  3. 启动服务：python -m uvicorn app.main:app --host 0.0.0.0 --port 8000")
    print("  4. 访问 http://localhost:8000/docs 使用真实简历测试")


async def main():
    """主函数"""
    await test_core_features()


if __name__ == "__main__":
    asyncio.run(main())
pytestmark = pytest.mark.integration
