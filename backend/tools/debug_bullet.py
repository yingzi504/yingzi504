"""调试模板段落中的项目符号设置"""
from pptx import Presentation
from lxml import etree

prs = Presentation(r'D:\ai_resume\backend\templates\New_Template_IAV_Resume_CN.pptx')
slide = prs.slides[0]

ns = '{http://schemas.openxmlformats.org/drawingml/2006/main}'

for shape in slide.shapes:
    if shape.has_table and shape.name == 'Group 262':
        table = shape.table
        cell = table.cell(0, 1)
        print("=== Work table cells ===")
        for i, para in enumerate(cell.text_frame.paragraphs):
            text = para.text
            pPr = para._p.find(f'{ns}pPr')
            if pPr is not None:
                buChar = pPr.find(f'{ns}buChar')
                buNone = pPr.find(f'{ns}buNone')
                print(f"\nPara[{i}]: text={repr(text)}")
                print(f"  buChar: {buChar.get('char') if buChar is not None else None}")
                print(f"  buNone: {'present' if buNone is not None else None}")
                print(f"  XML: {etree.tostring(pPr, pretty_print=True).decode()}")
            else:
                print(f"\nPara[{i}]: text={repr(text)}")
                print(f"  No pPr element")

    if shape.has_table and shape.name == 'Table 2':
        table = shape.table
        cell = table.cell(0, 1)
        print("\n=== Project table cells ===")
        for i, para in enumerate(cell.text_frame.paragraphs):
            text = para.text
            pPr = para._p.find(f'{ns}pPr')
            if pPr is not None:
                buChar = pPr.find(f'{ns}buChar')
                buNone = pPr.find(f'{ns}buNone')
                print(f"\nPara[{i}]: text={repr(text)}")
                print(f"  buChar: {buChar.get('char') if buChar is not None else None}")
                print(f"  buNone: {'present' if buNone is not None else None}")
                print(f"  XML: {etree.tostring(pPr, pretty_print=True).decode()}")
            else:
                print(f"\nPara[{i}]: text={repr(text)}")
                print(f"  No pPr element")
