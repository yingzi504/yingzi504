"""分析PPT输出内容"""
from pptx import Presentation

prs = Presentation(r'D:\ai_resume\resume_output (24).pptx')
for slide_idx, slide in enumerate(prs.slides):
    print('=== 第{}页 ==='.format(slide_idx + 1))
    for shape in slide.shapes:
        if shape.has_table:
            table = shape.table
            for row_idx, row in enumerate(table.rows):
                cells_text = []
                for cell in row.cells:
                    cells_text.append(cell.text.replace('\n', ' | '))
                print('  Row {}: {}'.format(row_idx, ' || '.join(cells_text)))
            print()
        elif shape.has_text_frame:
            text = shape.text_frame.text
            if text.strip():
                print('  [Text] {}'.format(text.strip()))
    print()
