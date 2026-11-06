"""检查 EN 模板的 tasks段落是否有 buChar"""
from pptx import Presentation

prs = Presentation(r'D:\ai_resume\backend\templates\New_Template_IAV_Resume_EN.pptx')
ns = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
for slide_idx, slide in enumerate(prs.slides):
    print(f"\n=== Slide {slide_idx} ===")
    for shape in slide.shapes:
        if shape.has_table:
            for row_idx, row in enumerate(shape.table.rows):
                for col_idx, cell in enumerate(row.cells):
                    for para_idx, para in enumerate(cell.text_frame.paragraphs):
                        text = para.text
                        if 'tasks' in text:
                            pPr = para._p.find(f'{ns}pPr')
                            buChar = pPr.find(f'{ns}buChar') if pPr is not None else None
                            buNone = pPr.find(f'{ns}buNone') if pPr is not None else None
                            print(f"  Shape={shape.name} Cell[{row_idx},{col_idx}] Para[{para_idx}]: buChar={'YES(' + buChar.get('char') + ')' if buChar is not None else 'NO'} buNone={'YES' if buNone is not None else 'NO'} text={repr(text[:60])}")
