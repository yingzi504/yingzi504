"""
PPT填充服务
使用python-pptx填充模板
"""
import os
import re
from typing import Dict, Any, Optional
from pptx import Presentation
from pptx.util import Pt
from pptx.enum.text import MSO_ANCHOR
from .template_config import (
    TEMPLATE_CONFIG, FIELD_MAPPING, TemplateType, Orientation, 
    ORIENTATION_TO_TEMPLATE, ARRAY_FIELDS, WORK_FIELDS, 
    PROJECT_FIELDS, EDUCATION_FIELDS
)
from app.schemas.resume import ResumeData
from app.core.config import settings


class FillerService:
    """PPT填充服务"""
    
    TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "..", "templates")
    OUTPUT_DIR = str(settings.output_path)
    
    @staticmethod
    def get_template_path(template_id: str) -> str:
        """获取模板文件路径"""
        if template_id not in TEMPLATE_CONFIG:
            raise ValueError(f"Unknown template: {template_id}")
        
        template_file = TEMPLATE_CONFIG[template_id]["file"]
        return os.path.join(FillerService.TEMPLATES_DIR, template_file)
    
    @staticmethod
    def get_value_from_path(data: Dict[str, Any], path: str) -> Any:
        """
        从数据字典中根据路径获取值
        
        支持的路径格式:
        - "name" -> data["name"]
        - "work[0].company" -> data["work"][0]["company"]
        """
        try:
            parts = path.split('.')
            current = data
            
            for part in parts:
                # 处理数组索引，如 work[0]
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
    def replace_text_in_run(run, replacements: Dict[str, str]) -> bool:
        """替换文本框中的占位符"""
        if not run.text:
            return False
        
        text = run.text
        replaced = False
        
        for placeholder, value in replacements.items():
            if placeholder in text:
                text = text.replace(placeholder, str(value))
                replaced = True
        
        if replaced:
            run.text = text
        
        return replaced
    
    @staticmethod
    def replace_text_in_paragraph(paragraph, replacements: Dict[str, str]) -> bool:
        """替换段落中的占位符（处理占位符被分割到多个runs的情况）"""
        if not paragraph.text:
            return False
        
        # 首先检查整个段落文本是否包含任何占位符
        full_text = paragraph.text
        has_placeholder = any(placeholder in full_text for placeholder in replacements)
        
        if not has_placeholder:
            return False
        
        # 方法1: 尝试在单个run级别替换（处理简单情况）
        replaced = False
        for run in paragraph.runs:
            if FillerService.replace_text_in_run(run, replacements):
                replaced = True
        
        if replaced:
            return True
        
        # 方法2: 如果占位符被分割到多个runs，重新构建整个段落
        # 保存第一个run的格式
        font_name = None
        font_size = None
        font_bold = None
        font_italic = None
        font_color = None
        
        if paragraph.runs:
            first_run = paragraph.runs[0]
            font_name = first_run.font.name
            font_size = first_run.font.size
            font_bold = first_run.font.bold
            font_italic = first_run.font.italic
            # 安全地获取颜色
            try:
                if first_run.font.color and hasattr(first_run.font.color, 'rgb'):
                    font_color = first_run.font.color.rgb
            except (AttributeError, ValueError):
                font_color = None
        else:
            # 如果没有runs，创建一个
            first_run = paragraph.add_run()
        
        # 执行替换
        new_text = full_text
        for placeholder, value in replacements.items():
            new_text = new_text.replace(placeholder, str(value))
        
        # 清除所有现有runs
        p = paragraph
        # 注意：python-pptx没有直接清除runs的方法
        # 替代方案：清空第一个run的文本，删除其他runs，然后设置文本
        if len(p.runs) > 0:
            # 清空第一个run
            p.runs[0].text = new_text
            # 恢复格式到第一个run
            if font_name:
                p.runs[0].font.name = font_name
            if font_size:
                p.runs[0].font.size = font_size
            if font_bold is not None:
                p.runs[0].font.bold = font_bold
            if font_italic is not None:
                p.runs[0].font.italic = font_italic
            if font_color:
                try:
                    p.runs[0].font.color.rgb = font_color
                except Exception:
                    pass  # 忽略颜色设置错误
            # 移除多余的runs（从后往前移除）
            while len(p.runs) > 1:
                p._p.remove(p.runs[-1]._r)
        
        return True
    
    @staticmethod
    def replace_text_in_shape(shape, replacements: Dict[str, str]) -> bool:
        """替换形状中的文本"""
        if not hasattr(shape, "text_frame"):
            return False
        
        replaced = False
        
        for paragraph in shape.text_frame.paragraphs:
            if FillerService.replace_text_in_paragraph(paragraph, replacements):
                replaced = True
        
        return replaced
    
    @staticmethod
    def replace_text_in_table(table, replacements: Dict[str, str]) -> bool:
        """替换表格中的文本"""
        replaced = False
        
        for row in table.rows:
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    if FillerService.replace_text_in_paragraph(paragraph, replacements):
                        replaced = True
        
        return replaced
    
    @staticmethod
    def build_replacements(resume_data: Dict[str, Any]) -> Dict[str, str]:
        """构建替换字典"""
        replacements = {}
        
        # 遍历基础字段映射
        for placeholder, data_path in FIELD_MAPPING.items():
            value = FillerService.get_value_from_path(resume_data, data_path)
            replacements[placeholder] = str(value) if value else ""
        
        # 为数组字段构建多索引的替换
        for array_name, config in ARRAY_FIELDS.items():
            data_array = resume_data.get(config["data_key"], [])
            
            # 为每个索引构建占位符（支持最多10条记录）
            for index in range(len(data_array)):
                for field_suffix, path_template in config["template"].items():
                    placeholder = f"{{{{{array_name}.{field_suffix}}}}}"
                    placeholder_with_index = f"{{{{{array_name}{index}.{field_suffix}}}}}"
                    
                    data_path = path_template.format(index=index)
                    value = FillerService.get_value_from_path(resume_data, data_path)
                    
                    # 支持带索引和不带索引的占位符
                    replacements[placeholder_with_index] = str(value) if value else ""
                    
                    # 不带索引的占位符只在 index=0 时设置一次
                    if index == 0:
                        replacements[placeholder] = str(value) if value else ""
        
        # 特殊处理：如果有脱敏姓名，优先使用
        if resume_data.get("anonymized_name"):
            replacements["{{name}}"] = resume_data["anonymized_name"]
        
        return replacements
    
    @staticmethod
    def _detect_array_row_pattern(paragraph_text: str) -> tuple:
        """检测段落文本是否包含数组占位符模式
        
        Returns:
            (array_name, field_name) 或 (None, None)
        """
        for array_name, config in ARRAY_FIELDS.items():
            prefix = config["placeholder_prefix"]
            if prefix in paragraph_text:
                # 提取字段名
                pattern = r'\{' + r'\{' + prefix + r'([^\}]+)\}\}'
                match = re.search(pattern, paragraph_text)
                if match:
                    return array_name, match.group(1)
        return None, None
    
    @staticmethod
    def _has_indexed_placeholder(paragraph_text: str, array_name: str) -> bool:
        """检查是否有带索引的占位符，如 {{work0.company}}"""
        pattern = r'\{' + r'\{' + array_name + r'\d+\.[^\}]+\}\}'
        return bool(re.search(pattern, paragraph_text))
    
    @staticmethod
    def _populate_array_rows(table, array_name: str, data_array: list, replacements: Dict[str, str]):
        """动态填充数组数据到表格行中"""
        if not data_array:
            return
        
        # 找到需要填充的起始行
        rows_to_process = []
        for row_index, row in enumerate(table.rows):
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    detected_array, _ = FillerService._detect_array_row_pattern(paragraph.text)
                    if detected_array == array_name:
                        rows_to_process.append((row_index, row))
                        break
                else:
                    continue
                break
        
        if not rows_to_process:
            return
        
        # 如果模板行有索引占位符，说明已经预留了多行
        has_indexed = FillerService._has_indexed_placeholder(
            table.rows[rows_to_process[0][0]].cells[0].text_frame.paragraphs[0].text,
            array_name
        )
        
        if has_indexed:
            # 模板已预留多行（带索引占位符），只需替换
            for i, (row_index, row) in enumerate(rows_to_process):
                if i >= len(data_array):
                    # 数据不够，清空剩余行
                    for cell in row.cells:
                        for paragraph in cell.text_frame.paragraphs:
                            for run in paragraph.runs:
                                run.text = ""
                else:
                    # 使用对应索引的替换字典
                    temp_replacements = {}
                    
                    # 构建针对这个索引的特定替换
                    for field_suffix, path_template in ARRAY_FIELDS[array_name]["template"].items():
                        placeholder = f"{{{{{array_name}.{field_suffix}}}}}"
                        placeholder_with_index = f"{{{{{array_name}{i}.{field_suffix}}}}}"
                        
                        data_path = path_template.format(index=i)
                        value = FillerService.get_value_from_path(
                            {array_name: data_array}, 
                            f"{array_name}[{i}].{field_suffix}"
                        )
                        
                        # 同时替换带索引和不带索引的占位符
                        temp_replacements[placeholder_with_index] = str(value) if value else ""
                        temp_replacements[placeholder] = str(value) if value else ""
                    
                    # 执行替换
                    for cell in row.cells:
                        for paragraph in cell.text_frame.paragraphs:
                            FillerService.replace_text_in_paragraph(paragraph, temp_replacements)
        else:
            # 模板只有一行不带索引的占位符，只填充第一条数据（向后兼容）
            # 填充找到的第一行
            _, first_row = rows_to_process[0]
            
            # 构建第一条数据的替换
            temp_replacements = {}
            for field_suffix, path_template in ARRAY_FIELDS[array_name]["template"].items():
                placeholder = f"{{{{{array_name}.{field_suffix}}}}}"
                value = FillerService.get_value_from_path(
                    {array_name: data_array},
                    f"{array_name}[0].{field_suffix}"
                )
                temp_replacements[placeholder] = str(value) if value else ""
            
            # 执行替换
            for cell in first_row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    FillerService.replace_text_in_paragraph(paragraph, temp_replacements)
    
    @staticmethod
    def fill_template(
        resume_data: ResumeData,
        template_type: Optional[TemplateType] = None,
        orientation: str = "vertical",
        output_filename: Optional[str] = None
    ) -> str:
        """
        填充PPT模板
        
        Args:
            resume_data: 简历数据
            template_type: 模板类型枚举 (TemplateType.ONEPAGER_CN, TemplateType.NEW_CN等)
            orientation: 模板方向 ("vertical" 或 "horizontal")，仅在未指定template_type时使用
            output_filename: 自定义输出文件名 (可选)
            
        Returns:
            输出文件路径
            
        Raises:
            ValueError: 参数无效
            FileNotFoundError: 模板文件不存在
            PermissionError: 没有写入权限
            Exception: 其他处理错误
        """
        try:
            # 1. 验证和准备数据
            if not resume_data:
                raise ValueError("简历数据不能为空")
            
            # 将ResumeData转换为字典
            resume_dict = resume_data.model_dump()
            
            # 2. 确定使用的模板
            if template_type:
                # 使用指定的模板类型
                if template_type not in TEMPLATE_CONFIG:
                    raise ValueError(f"无效的模板类型: {template_type}")
                template_id = template_type.value
            else:
                # 根据方向和语言选择默认模板
                try:
                    orient_enum = Orientation(orientation.lower())
                except ValueError:
                    raise ValueError(f"无效的模板方向: {orientation}，必须是 'vertical' 或 'horizontal'")
                
                language = resume_data.language or "CN"
                if language not in ORIENTATION_TO_TEMPLATE:
                    raise ValueError(f"不支持的语言: {language}")
                
                template_id = ORIENTATION_TO_TEMPLATE[language][orient_enum].value
            
            # 3. 确保输出目录存在且可写
            os.makedirs(FillerService.OUTPUT_DIR, exist_ok=True)
            if not os.access(FillerService.OUTPUT_DIR, os.W_OK):
                raise PermissionError(f"没有写入权限: {FillerService.OUTPUT_DIR}")
            
            # 4. 加载模板文件
            template_path = FillerService.get_template_path(template_id)
            if not os.path.exists(template_path):
                raise FileNotFoundError(f"模板文件不存在: {template_path}")
            
            try:
                prs = Presentation(template_path)
            except Exception as e:
                raise Exception(f"模板文件加载失败: {str(e)}")
            
            # 5. 构建替换字典
            replacements = FillerService.build_replacements(resume_dict)
            
            # 6. 执行替换
            try:
                for slide in prs.slides:
                    # 先处理普通形状
                    for shape in slide.shapes:
                        if not shape.has_table:
                            FillerService.replace_text_in_shape(shape, replacements)
                    
                    # 再处理表格（支持动态数组填充）
                    for shape in slide.shapes:
                        if shape.has_table:
                            table = shape.table
                            
                            # 先尝试动态填充数组数据
                            for array_name, config in ARRAY_FIELDS.items():
                                data_array = resume_dict.get(config["data_key"], [])
                                if data_array:
                                    FillerService._populate_array_rows(table, array_name, data_array, replacements)
                            
                            # 然后对表格进行常规替换
                            FillerService.replace_text_in_table(table, replacements)
            except Exception as e:
                raise Exception(f"模板内容替换失败: {str(e)}")
            
            # 7. 生成输出文件名
            if output_filename:
                output_filename = re.sub(r'[^\w\-_\.]', '_', output_filename)
                if not output_filename.endswith('.pptx'):
                    output_filename += '.pptx'
            else:
                job_position = resume_dict.get("position_en", None) or resume_dict.get("position", "resume") or "resume"
                language = TEMPLATE_CONFIG.get(template_id, {}).get("language", "CN")
                
                # 不论 CN/EN 输出，文件名一律使用英文敬称格式
                anon_en = resume_dict.get("anonymized_name", "")
                if anon_en and (anon_en.startswith("Mr.") or anon_en.startswith("Ms.")):
                    name = anon_en
                else:
                    name_cn = resume_dict.get("anonymized_name_cn", "")
                    gender = resume_dict.get("gender", "male") or "male"
                    if name_cn and len(name_cn) >= 2:
                        from app.services.anonymizer_service import AnonymizerService
                        surname_pinyin = AnonymizerService._chinese_name_to_pinyin(name_cn[0])
                        prefix = "Ms." if gender == "female" else "Mr."
                        name = f"{prefix}{surname_pinyin}"
                    else:
                        name = resume_dict.get("name", "output") or "output"
                
                safe_name = re.sub(r'[^\w\-_\.]', '_', name)
                safe_position = re.sub(r'[^a-zA-Z0-9\-\. ]', '', job_position)
                # 安全兜底：如果去除非ASCII字符后为空，使用'resume'
                safe_position = safe_position or 'resume'
                
                output_filename = f"IAV_{safe_name}_{safe_position}_Resume_{language}.pptx"
            
            output_path = os.path.join(FillerService.OUTPUT_DIR, output_filename)
            
            # 8. 保存文件
            try:
                prs.save(output_path)
            except PermissionError:
                raise PermissionError(f"无法保存文件，请关闭已打开的PPT: {output_path}")
            except Exception as e:
                raise Exception(f"文件保存失败: {str(e)}")
            
            # 9. 验证文件是否成功创建
            if not os.path.exists(output_path):
                raise Exception(f"文件创建失败: {output_path}")
            
            return output_path
            
        except ValueError as e:
            # 参数错误
            raise e
        except FileNotFoundError as e:
            # 文件不存在
            raise e
        except PermissionError as e:
            # 权限错误
            raise e
        except Exception as e:
            # 其他错误
            raise Exception(f"PPT填充失败: {str(e)}")

