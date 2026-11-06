"""Dump template XML for work table cell to understand run structure"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from pptx import Presentation
from lxml import etree

template_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 
    'templates', 'New_Template_IAV_Resume_CN.pptx')
prs = Presentation(template_path)

# Slide 1 - find work table
slide = prs.slides[0]
for shape in slide.shapes:
    if shape.has_table:
        t = shape.table
        print(f"Table: {len(t.rows)} rows, {len(t.columns)} cols")
        # Dump the template row (usually the only row or row 1)
        for ri in range(min(2, len(t.rows))):
            row = t.rows[ri]
            cells_text = []
            for ci, cell in enumerate(row.cells):
                cells_text.append(f"[{ci}] {cell.text[:80]}")
            print(f"  Row {ri}: {cells_text}")
            
            # Dump XML for cell 1 (the content cell)
            if len(row.cells) > 1:
                cell1 = row.cells[1]
                xml_str = etree.tostring(cell1._tc, pretty_print=True).decode()
                print(f"  Cell 1 XML:")
                print(xml_str[:5000])
            break
        break
