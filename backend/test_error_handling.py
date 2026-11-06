"""
测试改进的错误处理
"""
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.filler_service import FillerService
from app.services.template_config import TemplateType, Orientation


def test_error_handling():
    """测试各种错误场景"""
    print("=" * 70)
    print("  测试改进的错误处理")
    print("=" * 70)
    
    # 创建测试简历数据
    test_resume = ResumeData(
        name="Mr./Ms. Zhang",
        anonymized_name="Mr./Ms. Zhang",
        position="Software Engineer",
        technical_area="AI/ML",
        total_exp="5 years",
        language="EN",
        is_anonymized=True
    )
    
    # 测试1: 正常情况 - 应该成功
    print("\n[测试 1] 正常情况 (vertical)...")
    try:
        output_path = FillerService.fill_template(test_resume, orientation="vertical")
        print(f"  ✓ 成功: {output_path}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试2: 无效方向
    print("\n[测试 2] 无效方向...")
    try:
        output_path = FillerService.fill_template(test_resume, orientation="invalid")
        print(f"  ✗ 应该失败但成功了")
    except ValueError as e:
        print(f"  ✓ 正确捕获 ValueError: {e}")
    except Exception as e:
        print(f"  ✗ 错误的异常类型: {type(e).__name__}: {e}")
    
    # 测试3: 使用具体模板类型
    print("\n[测试 3] 使用具体模板类型 (NEW_EN)...")
    try:
        output_path = FillerService.fill_template(test_resume, template_type=TemplateType.NEW_EN)
        print(f"  ✓ 成功: {output_path}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试4: 自定义文件名
    print("\n[测试 4] 自定义文件名...")
    try:
        output_path = FillerService.fill_template(
            test_resume, 
            orientation="horizontal",
            output_filename="my_custom_resume"
        )
        print(f"  ✓ 成功: {output_path}")
    except Exception as e:
        print(f"  ✗ 失败: {e}")
    
    # 测试5: 空数据（应该失败）
    print("\n[测试 5] 空数据...")
    try:
        output_path = FillerService.fill_template(None, orientation="vertical")  # type: ignore
        print(f"  ✗ 应该失败但成功了")
    except ValueError as e:
        print(f"  ✓ 正确捕获 ValueError: {e}")
    except Exception as e:
        print(f"  ✗ 错误的异常类型: {type(e).__name__}: {e}")
    
    print("\n" + "=" * 70)
    print("测试完成")
    print("=" * 70)


if __name__ == "__main__":
    test_error_handling()
