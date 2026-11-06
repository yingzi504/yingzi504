"""
测试PPT模板填充服务
验证 Pipeline 步骤 6 的功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.filler_service import FillerService
from app.services.template_config import TemplateType


async def test_fill_template():
    """测试PPT模板填充"""
    print("=" * 60)
    print("测试：PPT模板填充（Pipeline 步骤 6）")
    print("=" * 60)
    
    # 创建测试简历数据
    test_resume = ResumeData(
        name="Mr./Ms. Zhang",
        anonymized_name="Mr./Ms. Zhang",
        phone="13800138000",
        email="zhangwei@example.com",
        location="北京市",
        age=28,
        birth_date="1995-05-15",
        position="Software Engineer",
        technical_area="AI/ML",
        total_exp="5 years",
        summary="具有5年Python开发经验，擅长机器学习和数据分析，参与过多个大型项目。",
        tech_skills="Python, TensorFlow, PyTorch, SQL, Docker",
        lang_skills="English, Japanese",
        lang_skills_level="Fluent",
        training_exp="Machine Learning Certification",
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
                tasks="负责后端开发和机器学习模型部署"
            ),
            WorkItem(
                company="Company B",
                period="2022-2024",
                role="Senior Software Engineer",
                tasks="负责系统架构设计"
            )
        ],
        project=[
            ProjectItem(
                company="Company A",
                period="2021-2022",
                name="Recommendation System",
                role="Core Developer",
                tasks="设计和实现推荐算法，提升用户留存率"
            )
        ],
        language="EN",
        is_anonymized=True
    )
    
    print("\n测试简历数据:")
    print(f"  姓名: {test_resume.name}")
    print(f"  职位: {test_resume.position}")
    print(f"  工作经历: {len(test_resume.work)} 条")
    print(f"  项目经历: {len(test_resume.project)} 条")
    
    # 测试纵向模板
    print("\n[测试 1] 纵向模板填充...")
    try:
        output_path = FillerService.fill_template(
            test_resume,
            orientation="vertical"
        )
        print(f"  ✓ 纵向模板填充成功: {output_path}")
        print(f"  ✓ 文件存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"  ✗ 纵向模板填充失败: {e}")
        import traceback
        traceback.print_exc()
    
    # 测试横向模板
    print("\n[测试 2] 横向模板填充...")
    try:
        output_path = FillerService.fill_template(
            test_resume,
            orientation="horizontal"
        )
        print(f"  ✓ 横向模板填充成功: {output_path}")
        print(f"  ✓ 文件存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"  ✗ 横向模板填充失败: {e}")
    
    # 测试指定模板类型
    print("\n[测试 3] 指定模板类型填充 (NEW_EN)...")
    try:
        output_path = FillerService.fill_template(
            test_resume,
            template_type=TemplateType.NEW_EN
        )
        print(f"  ✓ 指定模板填充成功: {output_path}")
        print(f"  ✓ 文件存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"  ✗ 指定模板填充失败: {e}")
    
    # 测试自定义文件名
    print("\n[测试 4] 自定义文件名...")
    try:
        output_path = FillerService.fill_template(
            test_resume,
            orientation="vertical",
            output_filename="custom_test_output"
        )
        print(f"  ✓ 自定义文件名成功: {output_path}")
        print(f"  ✓ 文件存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"  ✗ 自定义文件名失败: {e}")
    
    # 测试错误处理 - 无效方向
    print("\n[测试 5] 错误处理 - 无效方向...")
    try:
        output_path = FillerService.fill_template(
            test_resume,
            orientation="invalid"
        )
        print(f"  ✗ 应该抛出异常但没有")
    except ValueError as e:
        print(f"  ✓ 正确捕获异常: {e}")
    except Exception as e:
        print(f"  ✗ 捕获到错误类型的异常: {e}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


async def main():
    """主测试函数"""
    await test_fill_template()


if __name__ == "__main__":
    asyncio.run(main())
