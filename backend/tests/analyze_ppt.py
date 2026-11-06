"""分析指定PPT输出的文本内容"""
import sys
from pptx import Presentation

path = sys.argv[1] if len(sys.argv) > 1 else r'D:\ai_resume\backend\output\IAV_赵先生_标定工程师_Resume_CN.pptx'
prs = Presentation(path)
print(f'PPT: {path}')
print(f'总页数: {len(prs.slides)}')
print('='*80)

for slide_idx, slide in enumerate(prs.slides):
    print(f'\n=== 第{slide_idx+1}页 ===')
    for shape in slide.shapes:
        if shape.has_table:
            table = shape.table
            print(f'  [表格 {table.rows.__len__()}行 x {len(table.columns)}列]')
            for row_idx, row in enumerate(table.rows):
                cells_text = []
                for cell in row.cells:
                    t = cell.text.replace('\n', ' | ')
                    cells_text.append(t)
                print(f'    行{row_idx}: {" || ".join(cells_text)}')
        elif shape.has_text_frame:
            text = shape.text_frame.text
            if text.strip():
                print(f'  [文本框] {text.strip()[:200]}')
