"""
测试修复分割占位符的功能
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.filler_service import FillerService
from app.services.template_config import TemplateType


def test_split_placeholder_fix():
    """测试修复被分割的占位符"""
    print("=" * 70)
    print("  测试修复分割占位符")
    print("=" * 70)
    
    # 创建测试简历数据 - 包含更多字段
    test_resume = ResumeData(
        name="Li Song",
        anonymized_name="Li Song",
        position="Software Engineer",
        technical_area="Artificial Intelligence / Machine Learning",
        total_exp="8 years",
        summary="具有8年Python开发经验，擅长机器学习和数据分析。",
        tech_skills="Python, TensorFlow, PyTorch, SQL, Docker, Kubernetes",
        lang_skills="English, Japanese",
        lang_skills_level="Fluent",
        training_exp="Machine Learning Certification, AWS Certified",
        education=[
            EducationItem(
                period="2012-2016",
                school="Tsinghua University",
                degree="Bachelor",
                major="Computer Science"
            )
        ],
        work=[
            WorkItem(
                company="Company A",
                period="2016-2020",
                role="Software Engineer",
                tasks="负责后端开发和机器学习模型部署，参与多个大型项目。"
            ),
            WorkItem(
                company="Company B",
                period="2020-2024",
                role="Senior Software Engineer",
                tasks="负责系统架构设计，带领团队完成核心功能开发。"
            )
        ],
        project=[
            ProjectItem(
                company="Company A",
                period="2018-2020",
                name="智能推荐系统",
                role="Core Developer",
                tasks="设计和实现推荐算法，提升用户留存率30%。"
            )
        ],
        language="CN",
        is_anonymized=False
    )
    
    print("\n[测试 1] 使用新模板 (NEW_CN)...")
    try:
        output_path = FillerService.fill_template(
            test_resume,
            template_type=TemplateType.NEW_CN,
            output_filename="test_fix_split_placeholders"
        )
        print(f"  ✓ 成功生成: {output_path}")
        print(f"  ✓ 文件存在: {os.path.exists(output_path)}")
        print(f"  ✓ 文件大小: {os.path.getsize(output_path)} bytes")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n[测试 2] 使用横向模板 (ONEPAGER_CN)...")
    try:
        output_path = FillerService.fill_template(
            test_resume,
            template_type=TemplateType.ONEPAGER_CN,
            output_filename="test_onepager_fix"
        )
        print(f"  ✓ 成功生成: {output_path}")
        print(f"  ✓ 文件存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    
    print("\n" + "=" * 70)
    print("测试完成！请打开生成的PPT文件验证占位符是否被正确替换。")
    print("=" * 70)


if __name__ == "__main__":
    test_split_placeholder_fix()
