"""
分析PPT模板结构
"""
import os
import sys
from pptx import Presentation

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.filler_service import FillerService
from app.services.template_config import TemplateType


def analyze_template():
    """分析模板结构"""
    
    print("=" * 80)
    print("分析PPT模板结构")
    print("=" * 80)
    
    # 检查模板
    template_type = TemplateType.NEW_CN
    template_path = FillerService.get_template_path(template_type.value)
    
    if not os.path.exists(template_path):
        print(f"✗ 模板不存在: {template_path}")
        return
    
    print(f"\n分析模板: {template_type.value}")
    print(f"路径: {template_path}")
    
    prs = Presentation(template_path)
    
    print(f"\n幻灯片数量: {len(prs.slides)}")
    
    for slide_idx, slide in enumerate(prs.slides):
        print(f"\n--- 幻灯片 {slide_idx + 1} ---")
        
        # 统计表格
        table_count = 0
        for shape in slide.shapes:
            if shape.has_table:
                table_count += 1
                table = shape.table
                
                print(f"\n表格 {table_count}: {len(table.rows)} 行 x {len(table.columns)} 列")
                
                # 检查每行内容
                for row_idx, row in enumerate(table.rows):
                    row_text = []
                    has_placeholder = False
                    
                    for cell in row.cells:
                        cell_text = cell.text.strip()
                        row_text.append(cell_text)
                        
                        if "{{" in cell_text:
                            has_placeholder = True
                    
                    # 显示包含占位符的行
                    if has_placeholder:
                        print(f"  行 {row_idx + 1}: {' | '.join(row_text)}")
    
    print("\n" + "=" * 80)
    print("分析完成")
    print("=" * 80)
    
    print("\n建议:")
    print("1. 如果表格中只有1行工作经历占位符，")
    print("   需要在PPT中手动复制该行创建多行")
    print("2. 修改每行的占位符为: {{work0.company}}, {{work1.company}} 等")


if __name__ == "__main__":
    analyze_template()
