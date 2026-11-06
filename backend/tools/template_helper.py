"""
模板辅助工具 - 帮助修改PPT模板添加多行占位符
"""
import os
import sys
import shutil
from pptx import Presentation

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.template_config import TemplateType, ARRAY_FIELDS


def backup_template(template_path):
    """备份模板文件"""
    backup_path = template_path + '.backup'
    shutil.copy2(template_path, backup_path)
    print(f"✓ 模板已备份到: {backup_path}")
    return backup_path


def modify_template_for_multiple_rows(template_type):
    """修改模板添加多行支持"""
    
    print("=" * 80)
    print("PPT模板多行支持修改工具")
    print("=" * 80)
    
    from app.services.filler_service import FillerService
    
    template_path = FillerService.get_template_path(template_type.value)
    
    if not os.path.exists(template_path):
        print(f"✗ 模板不存在: {template_path}")
        return False
    
    print(f"\n模板: {template_type.value}")
    print(f"路径: {template_path}")
    
    # 备份
    backup_template(template_path)
    
    prs = Presentation(template_path)
    
    # 工作经历配置
    work_config = {
        'array_name': 'work',
        'placeholder_pattern': '{{work.',
        'num_rows': 3  # 支持3条工作经历
    }
    
    # 项目经历配置
    project_config = {
        'array_name': 'project',
        'placeholder_pattern': '{{project.',
        'num_rows': 2  # 支持2条项目经历
    }
    
    # 教育经历配置
    education_config = {
        'array_name': 'education',
        'placeholder_pattern': '{{education.',
        'num_rows': 2  # 支持2条教育经历
    }
    
    for slide_idx, slide in enumerate(prs.slides):
        for shape in slide.shapes:
            if shape.has_table:
                table = shape.table
                
                # 检查是否包含工作经历
                has_work = False
                for row in table.rows:
                    for cell in row.cells:
                        if '{{work.' in cell.text:
                            has_work = True
                            break
                    if has_work:
                        break
                
                if has_work:
                    print(f"\n在幻灯片 {slide_idx + 1} 找到工作经历表格")
                    print("当前模板只支持单行工作经历")
                    print("\n请按以下步骤手动修改模板:")
                    print("=" * 80)
                    print("\n1. 打开PPT模板文件:")
                    print(f"   {template_path}")
                    print("\n2. 找到工作经历区域，复制该行2次，得到3行")
                    print("\n3. 修改每行的占位符:")
                    print("\n   第1行:")
                    print("      {{work.period}} → {{work0.period}}")
                    print("      {{work.company}} → {{work0.company}}")
                    print("      {{work.role}} → {{work0.role}}")
                    print("      {{work.tasks}} → {{work0.tasks}}")
                    print("\n   第2行:")
                    print("      {{work.period}} → {{work1.period}}")
                    print("      {{work.company}} → {{work1.company}}")
                    print("      {{work.role}} → {{work1.role}}")
                    print("      {{work.tasks}} → {{work1.tasks}}")
                    print("\n   第3行:")
                    print("      {{work.period}} → {{work2.period}}")
                    print("      {{work.company}} → {{work2.company}}")
                    print("      {{work.role}} → {{work2.role}}")
                    print("      {{work.tasks}} → {{work2.tasks}}")
                    print("\n4. 对项目经历做同样处理 ({{project0.}}, {{project1.}})")
                    print("\n5. 对教育经历做同样处理 ({{education0.}}, {{education1.}})")
                    print("\n6. 保存模板")
                    print("\n" + "=" * 80)
                    print("修改完成后，再次运行测试:")
                    print("   python tests/test_filler_multiple_rows.py")
                    print("=" * 80)
    
    # 保存一个示例说明
    print("\n\n同时，让我生成一个示例说明文件...")
    
    # 不修改原文件，只给出说明
    return True


def check_template_status(template_type):
    """检查模板状态"""
    from app.services.filler_service import FillerService
    
    template_path = FillerService.get_template_path(template_type.value)
    
    if not os.path.exists(template_path):
        return False, "模板不存在"
    
    prs = Presentation(template_path)
    
    has_work0 = False
    has_work1 = False
    has_project0 = False
    has_education0 = False
    
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_table:
                for row in shape.table.rows:
                    for cell in row.cells:
                        text = cell.text
                        if '{{work0.' in text:
                            has_work0 = True
                        if '{{work1.' in text:
                            has_work1 = True
                        if '{{project0.' in text:
                            has_project0 = True
                        if '{{education0.' in text:
                            has_education0 = True
    
    status = []
    if has_work0 and has_work1:
        status.append("✓ 工作经历支持多行")
    else:
        status.append("✗ 工作经历需要修改")
    
    if has_project0:
        status.append("✓ 项目经历支持多行")
    else:
        status.append("✗ 项目经历需要修改")
    
    if has_education0:
        status.append("✓ 教育经历支持多行")
    else:
        status.append("✗ 教育经历需要修改")
    
    return has_work0 and has_project0 and has_education0, "\n".join(status)


if __name__ == "__main__":
    print("\n选择操作:")
    print("1. 检查模板状态")
    print("2. 查看模板修改指导")
    
    choice = input("\n请选择 (1/2): ").strip()
    
    if choice == "1":
        ok, status = check_template_status(TemplateType.NEW_CN)
        print(f"\n模板状态:\n{status}")
        if not ok:
            print("\n请按照说明修改模板")
    else:
        modify_template_for_multiple_rows(TemplateType.NEW_CN)
