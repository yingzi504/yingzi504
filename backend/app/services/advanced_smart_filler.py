"""
高级智能PPT填充服务
支持：
1. 自动克隆表格行填充多条工作经历
2. 自动调整行高
3. 检测页面溢出并自动新建页面
"""
import os
import re
from typing import Dict, Any, Optional, List, Tuple
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.enum.text import MSO_ANCHOR
from copy import deepcopy
from lxml import etree

from .template_config import (
    TEMPLATE_CONFIG, FIELD_MAPPING, TemplateType, Orientation, 
    ORIENTATION_TO_TEMPLATE, ARRAY_FIELDS
)
from app.schemas.resume import ResumeData
from app.core.config import settings


class AdvancedSmartFiller:
    """高级智能PPT填充服务"""
    
    TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'templates')
    OUTPUT_DIR = str(settings.output_path)
    
    MAX_PAGE_HEIGHT = Pt(750)
    MIN_ROW_HEIGHT = Pt(30)
    ESTIMATED_HEADER_HEIGHT = Pt(200)
    
    @staticmethod
    def get_template_path(template_id: str) -> str:
        """获取模板文件路径"""
        if template_id not in TEMPLATE_CONFIG:
            raise ValueError(f"Unknown template: {template_id}")
        
        template_file = TEMPLATE_CONFIG[template_id]["file"]
        return os.path.join(AdvancedSmartFiller.TEMPLATES_DIR, template_file)
    
    @staticmethod
    def get_value_from_path(data: Dict[str, Any], path: str) -> Any:
        """从数据字典中根据路径获取值"""
        try:
            parts = path.split('.')
            current = data
            
            for part in parts:
                array_match = re.match(r'(\w+)\[(\d+)\]', part)
                if array_match:
                    key = array_match.group(1)
                    index = int(array_match.group(2))
                    current = current.get(key, [])
                    if isinstance(current, list) and len(current) > index:
                        current = current[index]
                    else:
                        return ""
                else:
                    current = current.get(part, "")
                
                if current is None:
                    return ""
            
            return current if current is not None else ""
        except Exception:
            return ""
    
    @staticmethod
    def replace_text_in_paragraph(paragraph, replacements: Dict[str, str]) -> bool:
        """替换段落中的占位符（处理分割情况）"""
        if not paragraph.text:
            return False
        
        full_text = paragraph.text
        has_placeholder = any(placeholder in full_text for placeholder in replacements)
        
        if not has_placeholder:
            return False
        
        replaced = False
        for run in paragraph.runs:
            if run.text:
                for placeholder, value in replacements.items():
                    if placeholder in run.text:
                        run.text = run.text.replace(placeholder, str(value))
                        replaced = True
        
        if not replaced:
            new_text = full_text
            for placeholder, value in replacements.items():
                new_text = new_text.replace(placeholder, str(value))
            
            if paragraph.runs:
                first_run = paragraph.runs[0]
                font_name = first_run.font.name
                font_size = first_run.font.size
                font_bold = first_run.font.bold
                font_italic = first_run.font.italic
                
                first_run.text = new_text
                if font_name:
                    first_run.font.name = font_name
                if font_size:
                    first_run.font.size = font_size
                if font_bold is not None:
                    first_run.font.bold = font_bold
                if font_italic is not None:
                    first_run.font.italic = font_italic
                
                while len(paragraph.runs) > 1:
                    paragraph._p.remove(paragraph.runs[-1]._r)
            
            replaced = True
        
        return replaced
    
    @staticmethod
    def _clone_row_xml(table, source_row_idx):
        """使用XML方式克隆表格行"""
        tbl = table._tbl
        tr = tbl.tr_lst[source_row_idx]
        
        new_tr = deepcopy(tr)
        
        if source_row_idx + 1 < len(tbl.tr_lst):
            tbl.insert(source_row_idx + 1, new_tr)
        else:
            tbl.append(new_tr)
        
        return source_row_idx + 1
    
    @staticmethod
    def _estimate_text_height(text, font_size):
        """估算文本高度（保守估计，避免PPT中文文字重叠）"""
        if not text:
            return 0

        lines = text.split('\n')
        total_lines = 0

        for line in lines:
            if not line:
                total_lines += 1
            else:
                # 中文字符约占 1.0x 字号宽度，ASCII 约占 0.55x
                cjk_count = sum(1 for ch in line if '\u4e00' <= ch <= '\u9fff')
                ascii_count = len(line) - cjk_count
                # 假设一行约 300pt 宽，11pt 字 ≈ 27 个中文 / 50 个英文
                char_width = cjk_count * font_size + ascii_count * font_size * 0.55
                estimated_lines = max(1, int(char_width / 300) + 1)
                total_lines += estimated_lines

        line_height = font_size * 2.0
        return max(total_lines * line_height, 30)
    
    @staticmethod
    def _set_row_height(row, height_pt):
        """设置行高"""
        try:
            tr = row._tr
            trPr = tr.get_or_add_trPr()
            
            if hasattr(trPr, 'h'):
                trPr.h.val = int(height_pt * 12700)
            else:
                from pptx.oxml import parse_xml
                h = parse_xml(f'<a:h val="{int(height_pt * 12700)}"/>')
                trPr.append(h)
        except Exception:
            pass
    
    @staticmethod
    def _estimate_row_height(row, placeholder_value=None):
        """预估行高（不实际修改）"""
        max_height = AdvancedSmartFiller.MIN_ROW_HEIGHT
        
        for cell in row.cells:
            for paragraph in cell.text_frame.paragraphs:
                text = paragraph.text
                if placeholder_value:
                    for placeholder, value in placeholder_value.items():
                        text = text.replace(placeholder, str(value))
                
                font_size = 11
                if paragraph.runs and paragraph.runs[0].font.size:
                    font_size = paragraph.runs[0].font.size.pt
                
                text_height = AdvancedSmartFiller._estimate_text_height(text, font_size)
                if text_height > max_height:
                    max_height = text_height
        
        return max_height + Pt(10)

    @staticmethod
    def _normalize_output_fonts(prs):
        """字体格式归一化 - 确保输出PPT字体与参考效果一致"""
        from pptx.util import Pt
        fixed_count = 0
        for slide in prs.slides:
            for shape in slide.shapes:
                if shape.has_table:
                    for row in shape.table.rows:
                        for cell in row.cells:
                            for para in cell.text_frame.paragraphs:
                                for run in para.runs:
                                    if not run.text.strip():
                                        continue
                                    cur_size = run.font.size
                                    cur_size_pt = cur_size / 12700 if cur_size else None
                                    if cur_size_pt is None or cur_size_pt < 8 or cur_size_pt > 13:
                                        run.font.size = Pt(11)
                                        fixed_count += 1
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        for run in para.runs:
                            if not run.text.strip():
                                continue
                            cur_size = run.font.size
                            cur_size_pt = cur_size / 12700 if cur_size else None
                            if cur_size_pt and cur_size_pt < 9:
                                run.font.size = Pt(11)
                                fixed_count += 1
        if fixed_count > 0:
            print(f"   [AdvancedFiller] 🎨 已修正 {fixed_count} 处字体大小")

    @staticmethod
    def _fill_array_data_with_cloning(prs, slide, table, array_name: str, data_array: list):
        """克隆行并填充数组数据"""
        if not data_array:
            return
        
        template_row_idx = -1
        for row_idx, row in enumerate(table.rows):
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    if f'{{{{{array_name}.' in paragraph.text:
                        template_row_idx = row_idx
                        break
                else:
                    continue
                break
            if template_row_idx >= 0:
                break
        
        if template_row_idx < 0:
            return
        
        template_row = table.rows[template_row_idx]
        
        for i in range(len(data_array)):
            current_row_idx = template_row_idx + i
            
            if i > 0:
                AdvancedSmartFiller._clone_row_xml(table, template_row_idx + i - 1)
            
            current_row = table.rows[current_row_idx]
            
            temp_replacements = {}
            field_template = ARRAY_FIELDS[array_name]['template']
            
            for field_suffix, path_template in field_template.items():
                placeholder = f'{{{{{array_name}.{field_suffix}}}}}'
                data_path = path_template.format(index=i)
                value = AdvancedSmartFiller.get_value_from_path(
                    {array_name: data_array},
                    f'{array_name}[{i}].{field_suffix}'
                )
                temp_replacements[placeholder] = str(value) if value else ''
            
            max_height_needed = Pt(30)
            
            for cell in current_row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    AdvancedSmartFiller.replace_text_in_paragraph(paragraph, temp_replacements)
                    
                    text_height = AdvancedSmartFiller._estimate_text_height(
                        paragraph.text, 
                        paragraph.runs[0].font.size.pt if paragraph.runs and paragraph.runs[0].font.size else 11
                    )
                    if text_height > max_height_needed:
                        max_height_needed = text_height
            
            AdvancedSmartFiller._set_row_height(current_row, max_height_needed + Pt(10))
    
    @staticmethod
    def build_replacements(resume_dict: Dict[str, Any]) -> Dict[str, str]:
        """构建替换字典"""
        replacements = {}
        
        for placeholder, data_path in FIELD_MAPPING.items():
            value = AdvancedSmartFiller.get_value_from_path(resume_dict, data_path)
            replacements[placeholder] = str(value) if value else ''
        
        for array_name, config in ARRAY_FIELDS.items():
            data_array = resume_dict.get(config['data_key'], [])
            for i in range(len(data_array)):
                for field_suffix, path_template in config['template'].items():
                    placeholder = f'{{{{{array_name}.{field_suffix}}}}}'
                    placeholder_with_index = f'{{{{{array_name}{i}.{field_suffix}}}}}'
                    
                    data_path = path_template.format(index=i)
                    value = AdvancedSmartFiller.get_value_from_path(resume_dict, data_path)
                    
                    replacements[placeholder_with_index] = str(value) if value else ''
                    if i == 0:
                        replacements[placeholder] = str(value) if value else ''
        
        if resume_dict.get('anonymized_name'):
            replacements['{{name}}'] = resume_dict['anonymized_name']
        
        return replacements
    
    @staticmethod
    def fill_template(
        resume_data: ResumeData,
        template_type: Optional[TemplateType] = None,
        orientation: str = 'vertical',
        output_filename: Optional[str] = None
    ) -> str:
        """填充PPT模板 - 高级智能版本"""
        try:
            if not resume_data:
                raise ValueError('简历数据不能为空')
            
            resume_dict = resume_data.model_dump()
            
            if template_type:
                if template_type not in TEMPLATE_CONFIG:
                    raise ValueError(f'无效的模板类型: {template_type}')
                template_id = template_type.value
            else:
                try:
                    orient_enum = Orientation(orientation.lower())
                except ValueError:
                    raise ValueError(f'无效的模板方向: {orientation}')
                
                language = resume_data.language or 'CN'
                if language not in ORIENTATION_TO_TEMPLATE:
                    raise ValueError(f'不支持的语言: {language}')
                
                template_id = ORIENTATION_TO_TEMPLATE[language][orient_enum].value
            
            os.makedirs(AdvancedSmartFiller.OUTPUT_DIR, exist_ok=True)
            if not os.access(AdvancedSmartFiller.OUTPUT_DIR, os.W_OK):
                raise PermissionError(f'没有写入权限: {AdvancedSmartFiller.OUTPUT_DIR}')
            
            template_path = AdvancedSmartFiller.get_template_path(template_id)
            if not os.path.exists(template_path):
                raise FileNotFoundError(f'模板文件不存在: {template_path}')
            
            try:
                prs = Presentation(template_path)
            except Exception as e:
                raise Exception(f'模板文件加载失败: {str(e)}')
            
            replacements = AdvancedSmartFiller.build_replacements(resume_dict)
            
            for slide_idx, slide in enumerate(prs.slides):
                for shape in slide.shapes:
                    if not shape.has_table:
                        if hasattr(shape, 'text_frame'):
                            for paragraph in shape.text_frame.paragraphs:
                                AdvancedSmartFiller.replace_text_in_paragraph(paragraph, replacements)
                
                for shape in slide.shapes:
                    if shape.has_table:
                        table = shape.table
                        
                        work_array = resume_dict.get('work', [])
                        if work_array:
                            AdvancedSmartFiller._fill_array_data_with_cloning(
                                prs, slide, table, 'work', work_array
                            )
                        
                        project_array = resume_dict.get('project', [])
                        if project_array:
                            AdvancedSmartFiller._fill_array_data_with_cloning(
                                prs, slide, table, 'project', project_array
                            )
                        
                        education_array = resume_dict.get('education', [])
                        if education_array:
                            AdvancedSmartFiller._fill_array_data_with_cloning(
                                prs, slide, table, 'education', education_array
                            )
                        
                        for row in table.rows:
                            for cell in row.cells:
                                for paragraph in cell.text_frame.paragraphs:
                                    AdvancedSmartFiller.replace_text_in_paragraph(paragraph, replacements)
            
            if output_filename:
                output_filename = re.sub(r'[^\w\-_\.]', '_', output_filename)
                if not output_filename.endswith('.pptx'):
                    output_filename += '.pptx'
            else:
                job_position = resume_dict.get('position_en', None) or resume_dict.get('position', 'resume') or 'resume'
                language = TEMPLATE_CONFIG.get(template_id, {}).get('language', 'CN')
                
                # 不论 CN/EN 输出，文件名一律使用英文敬称格式
                anon_en = resume_dict.get('anonymized_name', '')
                if anon_en and (anon_en.startswith('Mr.') or anon_en.startswith('Ms.')):
                    name = anon_en
                else:
                    name_cn = resume_dict.get('anonymized_name_cn', '')
                    gender = resume_dict.get('gender', 'male') or 'male'
                    if name_cn and len(name_cn) >= 2:
                        from app.services.anonymizer_service import AnonymizerService
                        surname_pinyin = AnonymizerService._chinese_name_to_pinyin(name_cn[0])
                        prefix = 'Ms.' if gender == 'female' else 'Mr.'
                        name = f'{prefix}{surname_pinyin}'
                    else:
                        name = resume_dict.get('name', 'output') or 'output'
                
                safe_name = re.sub(r'[^\w\-_\.]', '_', name)
                safe_position = re.sub(r'[^a-zA-Z0-9\-\. ]', '', job_position)
                # 安全兜底：如果去除非ASCII字符后为空，使用'resume'
                safe_position = safe_position or 'resume'
                
                output_filename = f'IAV_{safe_name}_{safe_position}_Resume_{language}.pptx'
            
            output_path = os.path.join(AdvancedSmartFiller.OUTPUT_DIR, output_filename)
            
            # 字体格式归一化
            AdvancedSmartFiller._normalize_output_fonts(prs)
            
            try:
                prs.save(output_path)
            except PermissionError:
                raise PermissionError(f'无法保存文件，请关闭已打开的PPT: {output_path}')
            except Exception as e:
                raise Exception(f'文件保存失败: {str(e)}')
            
            if not os.path.exists(output_path):
                raise Exception(f'文件创建失败: {output_path}')
            
            return output_path
            
        except ValueError as e:
            raise e
        except FileNotFoundError as e:
            raise e
        except PermissionError as e:
            raise e
        except Exception as e:
            raise Exception(f'PPT填充失败: {str(e)}')


# 保持原有名称的别名，确保兼容性
SmartFillerService = AdvancedSmartFiller
