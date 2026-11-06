"""
完整重构的智能PPT填充服务 - 实现所有新需求
"""
import os
import re
from uuid import uuid4
from app.core.cv_rules import cv_download_filename
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple
from pptx import Presentation
from pptx.util import Pt, Inches
from pptx.enum.text import MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE_TYPE
from pptx.slide import SlideLayout
from copy import deepcopy
from lxml import etree
from fitz import get_text_length

from .template_config import (
    TEMPLATE_CONFIG, FIELD_MAPPING, TemplateType, Orientation, 
    ORIENTATION_TO_TEMPLATE, ARRAY_FIELDS
)
from app.schemas.resume import ResumeData
from app.core.config import settings
from app.core.cv_rules import CV_RULES


class PageConstraints:
    """页面约束配置"""
    
    # 第一页和新增页面的可输入范围
    REGULAR_PAGE_TOP_CM = 3.74
    REGULAR_PAGE_BOTTOM_CM = 26.47
    
    # 最后一页（模板第二页）的可输入范围
    LAST_PAGE_TOP_CM = 3.74
    LAST_PAGE_BOTTOM_CM = 23.54
    
    # 模块间距 — 缩小到0.5cm，减少框线间距以节省页面空间
    MODULE_SPACING_CM = CV_RULES.module_spacing_cm
    
    # 转换为EMU单位（正确的换算：1cm = 360,000 EMU）
    @staticmethod
    def cm_to_emu(cm: float) -> int:
        return int(cm * 360000)
    
    @staticmethod
    def emu_to_cm(emu: int) -> float:
        return emu / 360000
    
    # 预计算的EMU值
    REGULAR_PAGE_TOP = cm_to_emu.__func__(REGULAR_PAGE_TOP_CM)
    REGULAR_PAGE_BOTTOM = cm_to_emu.__func__(REGULAR_PAGE_BOTTOM_CM)
    LAST_PAGE_TOP = cm_to_emu.__func__(LAST_PAGE_TOP_CM)
    LAST_PAGE_BOTTOM = cm_to_emu.__func__(LAST_PAGE_BOTTOM_CM)
    MODULE_SPACING = cm_to_emu.__func__(MODULE_SPACING_CM)

    BODY_FONT_SIZE_PT = CV_RULES.body_font_size_pt
    # LibreOffice/PPT line metrics can exceed the python-pptx estimate by a
    # few points; keep enough room so the next module cannot cover the last line.
    ROW_SAFETY_MARGIN_PT = 8
    
    # 短经历段落按接近实际单行文字的高度计算，避免每条经历之间形成大段空白。
    # 多行职责仍按实际换行高度计算，并保留 fill_module_data 的安全余量。
    MIN_ROW_HEIGHT = Pt(12)


class ModuleInfo:
    """模块信息 - 可以包含标题文本框和表格作为一个整体"""
    def __init__(self, name: str, shape, table=None, slide=None, title_shape=None):
        self.name = name
        self.shape = shape  # 主形状（表格或单个文本框）
        self.table = table
        self.slide = slide
        self.title_shape = title_shape  # 标题文本框（可选）
        
        # 计算整体边界
        self._update_boundary()
        
        self.next_module = None  # 下一个模块
        self.data_array = []  # 该模块的数据
        self.is_table = shape.has_table  # 标记主形状是否是表格
    
    def _update_boundary(self):
        """更新模块的边界信息"""
        if self.title_shape:
            # 有标题的情况：取标题和主形状的最小top和最大bottom
            self.top = min(self.title_shape.top, self.shape.top)
            bottom_title = self.title_shape.top + (self.title_shape.height or 0)
            bottom_main = self.shape.top + (self.shape.height or 0)
            self.bottom = max(bottom_title, bottom_main)
            self.height = self.bottom - self.top
        else:
            # 没有标题的情况：只使用主形状
            self.top = self.shape.top
            self.height = self.shape.height or 0
            self.bottom = self.shape.top + self.height
    
    def move_down(self, distance: int):
        """向下移动整个模块（包括标题）"""
        if self.title_shape:
            self.title_shape.top += distance
        self.shape.top += distance
        self._update_boundary()


class PaginationState:
    """分页状态管理"""
    def __init__(self):
        self.current_page_idx = 0
        self.current_y = PageConstraints.REGULAR_PAGE_TOP  # 当前页面的Y位置


class SmartFillerService:
    """完整重构的智能PPT填充服务"""
    
    TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'templates')
    OUTPUT_DIR = str(settings.output_path)
    
    @staticmethod
    def get_page_constraints(slide_index: int, total_slides: int) -> Tuple[int, int]:
        """获取指定页面的约束范围"""
        if slide_index == total_slides - 1:
            return PageConstraints.LAST_PAGE_TOP, PageConstraints.LAST_PAGE_BOTTOM
        else:
            return PageConstraints.REGULAR_PAGE_TOP, PageConstraints.REGULAR_PAGE_BOTTOM
    
    @staticmethod
    def create_new_page(prs, source_slide_index: int = 0) -> Any:
        """
        创建新页面 - 复制第一页并清理内容
        
        参数:
            prs: Presentation对象
            source_slide_index: 源页面索引
            
        返回:
            新创建的Slide对象
        """
        print(f"   🆕 创建新页面，基于第{source_slide_index + 1}页")
        
        # 复制源页面
        source_slide = prs.slides[source_slide_index]
        new_slide = SmartFillerService._duplicate_slide_advanced(prs, source_slide)
        
        # 清理内容
        shapes_to_remove = []
        content_top = int(3.5 * 360000)   # 内容区顶部 ~3.5cm

        for shape in new_slide.shapes:
            # 跳过页眉页脚区域（顶部 < 3.5cm 和底部 > 26.5cm）
            shape_top_emu = shape.top
            shape_bottom_emu = shape.top + shape.height

            # 检查是否是默认文本框（如"单击输入标题"）
            is_default_textbox = False
            if shape.has_text_frame:
                text = shape.text.strip()
                if not text or "单击" in text or "Click to" in text or len(text) < 30:
                    # 检查是否是个人信息区域
                    is_personal_info = "{{name}}" in text or "Name：" in text or "姓名" in text
                    if not is_personal_info:
                        is_default_textbox = True

            # 检查是否是表格
            is_company_table = False
            if shape.has_table:
                table_text = ""
                for row in shape.table.rows:
                    for cell in row.cells:
                        table_text += cell.text
                if "IAV" in table_text and "Building" in table_text:
                    is_company_table = True

            # 检查是否是内容区的装饰性形状（无文本的 auto shape，会与新模块重叠）
            is_content_area = shape_top_emu >= content_top and shape_bottom_emu <= int(27 * 360000)
            # 使用 shape_type 而非 hasattr(auto_shape_type)，避免 Python 3.13 的 ValueError
            is_auto_shape = shape.shape_type == MSO_SHAPE_TYPE.AUTO_SHAPE
            is_decorative_shape = (
                is_auto_shape
                and is_content_area
                and not shape.has_text_frame
            ) or (
                is_auto_shape
                and is_content_area
                and shape.has_text_frame
                and not shape.text_frame.text.strip()
            )

            # 决定删除哪些
            if is_default_textbox or (shape.has_table and not is_company_table) or is_decorative_shape:
                shapes_to_remove.append(shape)
        
        # 删除形状
        for shape in reversed(shapes_to_remove):
            try:
                new_slide.shapes._spTree.remove(shape.element)
            except Exception:
                pass
        
        # 清空保留的个人信息文本框
        for shape in new_slide.shapes:
            if shape.has_text_frame:
                text = shape.text.strip()
                is_personal_info = "{{name}}" in text or "Name：" in text or "姓名" in text
                if is_personal_info:
                    for paragraph in shape.text_frame.paragraphs:
                        for run in paragraph.runs:
                            run.text = ""
                        paragraph.text = ""
        
        print(f"   ✅ 新页面创建完成，清理了{len(shapes_to_remove)}个形状")
        return new_slide
    
    @staticmethod
    def _duplicate_slide_advanced(prs, source_slide):
        """高级复制幻灯片"""
        # New pagination slides must not inherit title/body placeholders from
        # the source layout. Those layout placeholders are rendered by
        # PowerPoint even after the slide's default shapes are removed.
        slide_layout = next(
            (
                layout
                for layout in prs.slide_layouts
                if not any(getattr(shape, "is_placeholder", False) for shape in layout.shapes)
            ),
            source_slide.slide_layout,
        )
        new_slide = prs.slides.add_slide(slide_layout)
        
        # 删除默认形状
        shapes_to_remove = []
        for shape in new_slide.shapes:
            shapes_to_remove.append(shape)
        
        for shape in reversed(shapes_to_remove):
            try:
                new_slide.shapes._spTree.remove(shape.element)
            except Exception:
                pass
        
        # 复制源幻灯片形状
        for shape in source_slide.shapes:
            try:
                new_shape = SmartFillerService._clone_shape_element(shape, new_slide)
                new_slide.shapes._spTree.insert_element_before(new_shape, 'p:extLst')
            except Exception as e:
                print(f"复制形状时出错: {e}")
        
        return new_slide
    
    @staticmethod
    def collect_all_modules(prs) -> List[ModuleInfo]:
        """收集所有页面的所有模块"""
        all_modules = []
        
        for slide_idx, slide in enumerate(prs.slides):
            modules = SmartFillerService.collect_modules_on_slide(slide, slide_idx)
            all_modules.extend(modules)
        
        return all_modules
    
    @staticmethod
    def collect_modules_on_slide(slide, slide_idx: int) -> List[ModuleInfo]:
        """
        收集单个页面上的模块 - 将标题文本框和表格作为一个整体
        
        返回按位置排序的模块列表
        """
        modules = []
        module_names = ['work', 'project', 'education', 'skill']
        
        # 首先收集所有形状并分类
        all_shapes = []
        company_table = None
        
        for shape in slide.shapes:
            # 检查是否是公司表格
            if shape.has_table:
                table_text = ""
                for row in shape.table.rows:
                    for cell in row.cells:
                        table_text += cell.text
                if "IAV" in table_text and "Building" in table_text:
                    company_table = shape
                    continue
            
            all_shapes.append({
                'shape': shape,
                'top': shape.top,
                'is_table': shape.has_table,
                'text': shape.text.strip() if hasattr(shape, 'text_frame') else ''
            })
        
        # 按top排序所有形状
        all_shapes.sort(key=lambda x: x['top'])
        
        # 识别和配对标题与表格
        used_indices = set()
        # 关键词统一使用小写，匹配时对标题文本做大小写不敏感比较，
        # 避免英文模板中全大写的标题（如"WORK EXPERIENCE"、"QUALIFICATION"）
        # 无法被正确识别，导致标题与表格配对失败。
        module_titles = {
            'work': ['工作经历', '工作经验', 'work'],
            'project': ['项目经历', '项目经验', 'project'],
            'education': ['教育经历', '教育背景', 'education', 'training'],
            'skill': ['职业技能', '技能', 'skill', 'skills', 'qualification']
        }
        
        for i, shape_info in enumerate(all_shapes):
            if i in used_indices:
                continue
            
            shape = shape_info['shape']
            shape_text = shape_info['text']
            shape_text_lower = shape_text.lower()
            is_table = shape_info['is_table']
            
            # 检查是否是标题文本框（大小写不敏感）
            title_name = None
            for name, keywords in module_titles.items():
                for keyword in keywords:
                    if keyword in shape_text_lower:
                        title_name = name
                        break
                if title_name:
                    break
            
            # 情况1：找到了标题，尝试找下方的表格
            if title_name and not is_table:
                # 查找下方最近的表格（允许的距离内）
                table_shape = None
                table_idx = -1
                max_distance = 500000  # 约1.4cm的最大距离
                
                for j in range(i + 1, len(all_shapes)):
                    candidate = all_shapes[j]
                    if candidate['is_table']:
                        distance = candidate['top'] - shape_info['top']
                        if 0 < distance < max_distance:
                            table_shape = candidate['shape']
                            table_idx = j
                            break
                
                if table_shape:
                    # 找到表格，创建包含标题和表格的模块
                    modules.append(ModuleInfo(
                        title_name, 
                        table_shape, 
                        table_shape.table if table_shape.has_table else None, 
                        slide,
                        title_shape=shape
                    ))
                    used_indices.add(i)
                    used_indices.add(table_idx)
                    continue
            
            # 情况2：直接识别表格模块（没有标题的情况）
            if is_table:
                module_name = None
                table = shape.table
                
                # 检查表格属于哪个模块
                for row in table.rows:
                    for cell in row.cells:
                        cell_text = cell.text
                        for name in module_names:
                            if f'{{{{{name}.' in cell_text:
                                module_name = name
                                break
                        if module_name:
                            break
                    if module_name:
                        break
                
                # 特殊处理skill
                if not module_name:
                    for row in table.rows:
                        for cell in row.cells:
                            if '{{lang_skills' in cell.text or '{{tech_skills' in cell.text:
                                module_name = 'skill'
                                break
                        if module_name:
                            break
                
                if module_name and i not in used_indices:
                    modules.append(ModuleInfo(
                        module_name, 
                        shape, 
                        table, 
                        slide
                    ))
                    used_indices.add(i)
        
        # 按位置排序
        modules.sort(key=lambda m: m.top)
        
        # 设置next_module引用
        for i in range(len(modules) - 1):
            modules[i].next_module = modules[i + 1]
        
        return modules
    
    @staticmethod
    def copy_module_to_slide(module: ModuleInfo, target_slide, new_top: int) -> Optional[ModuleInfo]:
        """
        复制模块到目标页面
        
        参数:
            module: 源模块
            target_slide: 目标幻灯片
            new_top: 新的顶部位置
            
        返回:
            新创建的模块信息
        """
        # 复制形状
        new_shape_element = SmartFillerService._clone_shape_element(
            module.shape, target_slide
        )
        target_slide.shapes._spTree.insert_element_before(new_shape_element, 'p:extLst')
        
        # 找到新创建的形状
        new_shape = None
        for shape in target_slide.shapes:
            if shape.element is new_shape_element:
                new_shape = shape
                break
        
        if not new_shape:
            # 如果找不到，尝试通过位置找到
            for shape in target_slide.shapes:
                if shape.has_table == module.shape.has_table:
                    if shape.top == module.shape.top:
                        new_shape = shape
                        break
        
        if new_shape:
            new_shape.top = new_top
            new_module = ModuleInfo(
                module.name, 
                new_shape, 
                new_shape.table if new_shape.has_table else None,
                target_slide
            )
            return new_module
        
        return None
    
    @staticmethod
    def estimate_row_height(row, table, replacements: Dict[str, str], 
                          data_item: Any, array_name: str, item_index: int) -> int:
        """估算单行高度
        
        关键：使用 sum(非任务段落) + max(任务段落)，而非纯 max。
        
        fill_module_data() 将 tasks 逐项分配到独立段落，用 sum 计算实际行高。
        本函数若只用 max，会严重低估（work 模块 7 段落中 max 约 90pt，
        但实际 sum 达 165pt），导致分页估算错误、内容溢出页面、元素重叠。
        
        任务段落全部包含相同的完整 task 文本，所以仅取一次 max 即可；
        非任务段落各自含不同内容（company/role/responsibility），需要 sum。
        """
        if array_name in ARRAY_FIELDS:
            field_template = ARRAY_FIELDS[array_name]['template']
            temp_replacements = {}
            for field_suffix, path_template in field_template.items():
                placeholder = f'{{{{{array_name}.{field_suffix}}}}}'
                value = SmartFillerService.get_value_from_path(
                    {array_name: [data_item]},
                    f'{array_name}[0].{field_suffix}'
                )
                value_str = str(value) if value else ''
                if field_suffix == 'tasks' and value_str:
                    value_str = SmartFillerService._normalize_task_bullets(value_str)
                temp_replacements[placeholder] = value_str
        else:
            # 不在 ARRAY_FIELDS 中的模块（如 skill），使用全局 replacements
            temp_replacements = {}
            for placeholder, value in replacements.items():
                temp_replacements[placeholder] = str(value) if value else ''
        
        tasks_placeholders = [p for p in temp_replacements if p.endswith('.tasks}}')]
        
        # 各列取最大 cell_total_height 作为行高估算值
        max_cell_total_height_pt = PageConstraints.MIN_ROW_HEIGHT.pt
        
        for col_idx, cell in enumerate(row.cells):
            if col_idx < len(table.columns):
                cell_width = table.columns[col_idx].width
            else:
                cell_width = Pt(200)
            
            # 分离任务段落和其他段落
            # - 非任务段落: sum 累加（每段内容唯一）
            # - 任务段落: 只取 max（每段都被同一完整 task 文本填充）
            non_task_sum = 0.0
            task_max = 0.0
            
            for paragraph in cell.text_frame.paragraphs:
                estimated_text = paragraph.text
                for tp in tasks_placeholders:
                    estimated_text = estimated_text.replace(f'• {tp}', tp)
                    estimated_text = estimated_text.replace(f'•{tp}', tp)
                for placeholder, value in temp_replacements.items():
                    estimated_text = estimated_text.replace(placeholder, str(value))
                
                font_size = PageConstraints.BODY_FONT_SIZE_PT
                
                text_height = SmartFillerService._estimate_text_height(
                    estimated_text,
                    font_size,
                    cell_width,
                    line_spacing_factor=1.0 if array_name == 'work' else 1.2,
                ).pt
                
                is_task_para = any(tp in paragraph.text for tp in tasks_placeholders)
                if is_task_para:
                    task_max = max(task_max, text_height)
                else:
                    non_task_sum += text_height
            
            cell_total = non_task_sum + task_max
            if cell_total > max_cell_total_height_pt:
                max_cell_total_height_pt = cell_total
        
        # +15pt 安全余量，与 fill_module_data 保持一致，防止PPT实际渲染溢出
        return int((max_cell_total_height_pt + PageConstraints.ROW_SAFETY_MARGIN_PT) * 12700)
    
    @staticmethod
    def _estimate_text_height(
        text: str,
        font_size: float,
        estimated_width=None,
        line_spacing_factor: float = 1.2,
    ) -> Pt:
        """Estimate wrapped Arial text using Latin glyph widths and CJK em widths."""
        if not text:
            return Pt(0)

        if not estimated_width:
            estimated_width = Pt(400)

        if hasattr(estimated_width, 'pt'):
            width_pt = estimated_width.pt
        else:
            width_pt = 400

        # 扣除默认单元格左右边距（约 0.05in = 3.6pt 每侧）
        effective_width = max(20, width_pt - 14)

        # Helvetica has Arial-compatible Latin metrics. Wrap at word boundaries;
        # CJK glyphs occupy one em and can wrap between characters.
        cjk_count = sum(1 for ch in text if '\u2e80' <= ch <= '\uffef')
        total_lines = 0
        for line in text.split('\n'):
            lines, used = 1, 0.0
            for token in re.findall(r'[\u2e80-\uffef]|[^\s\u2e80-\uffef]+|[^\S\n]+', line):
                width = (font_size if len(token) == 1 and '\u2e80' <= token <= '\uffef'
                         else get_text_length(token, fontname='helv', fontsize=font_size))
                if used and used + width > effective_width:
                    lines += 1
                    used = 0.0
                    if token.isspace():
                        continue
                while width > effective_width:
                    lines += 1
                    width -= effective_width
                used += width
            total_lines += lines

        line_height = font_size * max(line_spacing_factor, 1.35 if cjk_count else 1.2)
        return Pt(max(total_lines * line_height, PageConstraints.MIN_ROW_HEIGHT.pt))
    
    @staticmethod
    def _normalize_task_bullets(tasks_text: str) -> str:
        """统一 tasks 文本每行的项目符号：去掉已有符号再统一加 •
        
        处理内容包括：
        - 移除每行开头所有连续的项目符号字符（避免重复符号）
        - 移除每行末尾的分号（项目符号已表示列表项，分号冗余）
        - 移除行尾已有的句尾标点（句号、感叹号、问号等）
        - 过滤空行后统一添加单个 •
        """
        import re
        lines = tasks_text.split('\n')
        # 匹配行首任意数量的项目符号字符（用 + 确保连续多个也被一并移除）
        bullet_pattern = re.compile(r'^[\s]*[•·▪▸►●○◆◇❖➢✓✔☑▪▫\-*\u2022\u2023\u25E6\u2043\u2219]+\s*')
        cleaned_lines = []
        for line in lines:
            line = bullet_pattern.sub('', line).strip()
            # 移除行尾分号（项目符号已表示列表项，分号冗余）
            line = line.rstrip(';')
            line = line.strip()
            if line:
                # 移除行尾所有标点符号
                line = re.sub(r'[。.!！?？，,、；;：:…—～~]+$', '', line).strip()
                cleaned_lines.append(line)
        # 过滤空行，统一加 • 
        return '\n'.join(f'• {line}' for line in cleaned_lines if line)
    
    @staticmethod
    def _split_oversized_item(
        module: ModuleInfo,
        data_item: Any,
        replacements: Dict[str, str],
        available_height: int,
    ) -> List[Any]:
        """Split one work/project row into page-sized continuation rows."""
        if module.name not in ("work", "project") or not module.table:
            return [data_item]
        raw_tasks = (
            data_item.get("tasks", "") if isinstance(data_item, dict)
            else getattr(data_item, "tasks", "")
        )
        if not raw_tasks or not str(raw_tasks).strip():
            return [data_item]

        template_row = next(
            (
                row for row in module.table.rows
                if any(f"{{{{{module.name}." in cell.text for cell in row.cells)
            ),
            None,
        )
        if template_row is None:
            return [data_item]

        clauses = [
            part.strip()
            for part in re.split(
                r'(?:\r?\n)+|;\s*|(?<=[.!?\u3002\uff01\uff1f])\s+',
                str(raw_tasks),
            )
            if part.strip()
        ]
        def with_tasks(value: str):
            if isinstance(data_item, dict):
                clone = deepcopy(data_item)
                clone["tasks"] = value
                return clone
            if hasattr(data_item, "model_copy"):
                return data_item.model_copy(deep=True, update={"tasks": value})
            clone = deepcopy(data_item)
            setattr(clone, "tasks", value)
            return clone

        def fits(parts: List[str]) -> bool:
            candidate = with_tasks("\n".join(parts))
            height = SmartFillerService.estimate_row_height(
                template_row, module.table, replacements, candidate, module.name, 0
            )
            return height <= available_height

        groups: List[List[str]] = []
        current: List[str] = []
        for clause in clauses:
            candidate = current + [clause]
            if fits(candidate):
                current = candidate
                continue
            if current:
                groups.append(current)
                current = []
            words = clause.split()
            word_group: List[str] = []
            for word in words:
                word_candidate = [" ".join(word_group + [word])]
                if word_group and not fits(word_candidate):
                    groups.append([" ".join(word_group)])
                    word_group = [word]
                else:
                    word_group.append(word)
            if word_group:
                current = [" ".join(word_group)]
        if current:
            groups.append(current)

        if len(groups) <= 1:
            return [data_item]
        return [with_tasks("\n".join(group)) for group in groups]
    @staticmethod
    def calculate_pagination_for_module(module: ModuleInfo, data_array: List[Any],
                                       replacements: Dict[str, str], start_y: int,
                                       page_top: int, page_bottom: int) -> Tuple[int, int]:
        """
        计算模块的分页点
        
        参数:
            module: 模块信息
            data_array: 数据数组
            replacements: 替换字典
            start_y: 起始Y位置
            page_top: 页面顶部限制
            page_bottom: 页面底部限制
            
        返回:
            (当前页能放的数量, 剩余数据起始索引)
        """
        if not module.table or not data_array:
            return len(data_array), len(data_array)
        
        # 找到模板行
        template_row_idx = -1
        for row_idx, row in enumerate(module.table.rows):
            for cell in row.cells:
                if f'{{{{{module.name}.' in cell.text:
                    template_row_idx = row_idx
                    break
            if template_row_idx >= 0:
                break
        
        # 特殊处理skill
        if template_row_idx < 0 and module.name == 'skill':
            for row_idx, row in enumerate(module.table.rows):
                for cell in row.cells:
                    if '{{lang_skills' in cell.text or '{{tech_skills' in cell.text:
                        template_row_idx = row_idx
                        break
                if template_row_idx >= 0:
                    break
        
        if template_row_idx < 0:
            return len(data_array), len(data_array)
        
        template_row = module.table.rows[template_row_idx]
        
        # 计算固定高度（不包括模板行）
        fixed_height = 0
        for row_idx, row in enumerate(module.table.rows):
            if row_idx < template_row_idx:
                if row.height:
                    fixed_height += row.height
                else:
                    fixed_height += int(PageConstraints.MIN_ROW_HEIGHT.pt * 12700)
        
        current_y = start_y + fixed_height
        count = 0
        
        for i, data_item in enumerate(data_array):
            row_height = SmartFillerService.estimate_row_height(
                template_row, module.table, replacements, data_item, module.name, i
            )
            
            if current_y + row_height > page_bottom:
                print(f"   📏 第{i}行后溢出，当前页能放{count}行")
                return count, i
            
            current_y += row_height
            count += 1
        
        return count, len(data_array)
    
    @staticmethod
    def fill_module_data(module: ModuleInfo, data_array: List[Any],
                        replacements: Dict[str, str], start_idx: int = 0,
                        end_idx: Optional[int] = None):
        """填充模块数据"""
        if end_idx is None:
            end_idx = len(data_array)
        
        if not module.table or start_idx >= end_idx:
            return
        
        # 找到模板行
        template_row_idx = -1
        for row_idx, row in enumerate(module.table.rows):
            for cell in row.cells:
                if f'{{{{{module.name}.' in cell.text:
                    template_row_idx = row_idx
                    break
            if template_row_idx >= 0:
                break
        
        if template_row_idx < 0 and module.name == 'skill':
            for row_idx, row in enumerate(module.table.rows):
                for cell in row.cells:
                    if '{{lang_skills' in cell.text or '{{tech_skills' in cell.text:
                        template_row_idx = row_idx
                        break
                if template_row_idx >= 0:
                    break
        
        if template_row_idx < 0:
            return
        
        template_row = module.table.rows[template_row_idx]
        template_tr_xml = deepcopy(template_row._tr)
        
        # 先填充其他字段（跳过模板数据行，由后续数据填充循环处理，
        # 避免非索引占位符如 {{project.company}} 被全局替换后，
        # 数据循环无法匹配到正确的逐行数据）
        for ri, row in enumerate(module.table.rows):
            if ri == template_row_idx:
                continue
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    SmartFillerService.replace_text_in_paragraph(paragraph, replacements)
        
        # 填充数据行
        for i in range(start_idx, end_idx):
            current_row_idx = template_row_idx + (i - start_idx)
            
            # 克隆新行
            if i > start_idx:
                tbl = module.table._tbl
                new_tr = deepcopy(template_tr_xml)
                insert_pos = template_row_idx + (i - start_idx)
                if insert_pos < len(tbl.tr_lst):
                    tbl.insert(insert_pos, new_tr)
                else:
                    tbl.append(new_tr)
            
            current_row = module.table.rows[current_row_idx]
            
            # 构建替换字典
            temp_replacements = dict(replacements) if module.name not in ARRAY_FIELDS else {}
            if module.name in ARRAY_FIELDS:
                field_template = ARRAY_FIELDS[module.name]['template']
                for field_suffix, path_template in field_template.items():
                    placeholder = f'{{{{{module.name}.{field_suffix}}}}}'
                    value = SmartFillerService.get_value_from_path(
                        {module.name: data_array},
                        f'{module.name}[{i}].{field_suffix}'
                    )
                    value_str = str(value) if value else ''

                    # Keep the template project.company + project.name heading.
                    if module.name == 'project' and field_suffix == 'name' and not value_str:
                        value_str = 'Project' if replacements.get('{{language}}', '').upper() == 'EN' else '某项目'
                    
                    # tasks 字段：统一每行添加项目符号
                    if field_suffix == 'tasks' and value_str:
                        value_str = SmartFillerService._normalize_task_bullets(value_str)
                    
                    temp_replacements[placeholder] = value_str
            
            # 填充并计算高度
            # 单元格行高 = Σ(所有段落高度)，而非 MAX(单个段落)
            # 根因：模板行有多段落堆叠（如 work 模块有 7 段：
            # company/role/职责/3×任务/空段），各段独立占垂直空间。
            # 若仅取 max，行高只够容纳一段，其余段溢出到下一行。
            max_cell_height = PageConstraints.MIN_ROW_HEIGHT
            
            # 收集 tasks 占位符（用于处理模板中已有的项目符号）
            tasks_placeholders = [p for p in temp_replacements if p.endswith('.tasks}}')]
            
            for col_idx, cell in enumerate(current_row.cells):
                if col_idx < len(module.table.columns):
                    cell_width = module.table.columns[col_idx].width
                else:
                    cell_width = Pt(200)
                
                cell_total_height = Pt(0)
                
                # tasks 多行分布到各段落：
                # 模板中可能有多个 {{module.tasks}} 段落（如 3 个 bullet），
                # 将 tasks 的每项内容分配到不同段落，让每个 • 独占一个段落。
                # 
                # 为什么必须这样做？
                # PPTX 中 \n 只创建 line break（同一段落内换行），
                # 段落缩进（marL + indent）只作用于段落首行，
                # 同一段落中 line break 换行后的行从 marL 开始（不叠加 indent）。
                # 如果所有任务项都在同一段落中用 \n 分隔，
                # 只有第一个 • 在 position 0，后续 • 都在 marL 位置。
                # 
                # 分配到不同段落 → 每个 • 独占段落首行 → 悬挂缩进正确生效：
                # • 任务描述文字内容    ← marL+indent=0
                #   任务描述换行文字    ← marL（与第一行文字对齐）
                # • 第二条任务描述      ← marL+indent=0
                #   第二条换行文字      ← marL（与第一行文字对齐）
                tasks_pool = {}
                for tp in tasks_placeholders:
                    val = temp_replacements.get(tp, '')
                    items = [t.strip() for t in val.split('\n') if t.strip()]
                    if items:
                        tasks_pool[tp] = list(items)
                # 统计每个占位符出现的段落总数
                tp_para_counts = {}
                for tp in tasks_placeholders:
                    tp_para_counts[tp] = sum(1 for p in cell.text_frame.paragraphs if tp in p.text)

                # 职责段落统一使用悬挂缩进：项目符号位于单元格左边界，职责文字和
                # 后续换行从同一个文本起始位置开始。固定使用 101600 EMU（约 8pt），
                # 避免部分模板的 171450 EMU 在 LibreOffice 渲染时让换行额外右移。
                task_marL = '101600'
                
                # 确保段落数 ≥ 任务项数：不足时克隆最后一个段落
                # 每个 • 必须独占一个段落，否则 \n 续行的 • 会渲染在 marL 位置而非 position 0
                for tp in tasks_placeholders:
                    if tp not in tasks_pool or not tasks_pool[tp]:
                        continue
                    n_items = len(tasks_pool[tp])
                    n_paras = tp_para_counts.get(tp, 0)
                    if n_items > n_paras:
                        # 找到最后一个包含此占位符的段落
                        last_tp_para = None
                        for p in cell.text_frame.paragraphs:
                            if tp in p.text:
                                last_tp_para = p
                        if last_tp_para is not None:
                            extra = n_items - n_paras
                            for _ in range(extra):
                                new_p_elem = deepcopy(last_tp_para._p)
                                last_tp_para._p.addnext(new_p_elem)
                                tp_para_counts[tp] = tp_para_counts.get(tp, 0) + 1
                
                tp_para_seen = {}
                tasks_exhausted = set()
                
                for para_idx, paragraph in enumerate(cell.text_frame.paragraphs):
                    # 模板中已有 • 前缀时，去掉它（我们的值已统一带 •）
                    for tp in tasks_placeholders:
                        for run in paragraph.runs:
                            if run.text:
                                run.text = run.text.replace(f'• {tp}', tp)
                                run.text = run.text.replace(f'•{tp}', tp)
                    
                    is_task_para = any(tp in paragraph.text for tp in tasks_placeholders)
                    
                    # 确保所有段落都有 pPr 元素
                    pPr = paragraph._p.find('{http://schemas.openxmlformats.org/drawingml/2006/main}pPr')
                    if pPr is None:
                        pPr = etree.SubElement(paragraph._p,
                            '{http://schemas.openxmlformats.org/drawingml/2006/main}pPr')

                    # 每个段落都有自己的文本起始位置，不能把任务段落的 marL
                    # 复用到时间、公司、项目名称等普通段落。部分中文项目模板的
                    # 任务段落使用 171450 的悬挂缩进，但普通段落没有 marL；旧逻辑
                    # 会因此把整个项目单元格（甚至时间单元格的默认值）右移。
                    paragraph_marL = pPr.get('marL', '0')
                    
                    if is_task_para:
                        # ── 任务段落：悬挂缩进 ──
                        # bullet • 在位置 0（marL + indent = 0），续行文字从 marL 开始
                        # 这样 task 文字与 company/role 文字左对齐一致
                        buChar = pPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}buChar')
                        buNone = pPr.find('{http://schemas.openxmlformats.org/drawingml/2006/main}buNone')
                        if buChar is not None and buNone is None:
                            for tag in ('buChar', 'buFont', 'buClrTx', 'buSzTx', 'buFontTx'):
                                elem = pPr.find(f'{{http://schemas.openxmlformats.org/drawingml/2006/main}}{tag}')
                                if elem is not None:
                                    pPr.remove(elem)
                            etree.SubElement(pPr, '{http://schemas.openxmlformats.org/drawingml/2006/main}buNone')

                        # 悬挂缩进：bullet 从 0 开始，续行从 marL 开始
                        pPr.set('marL', task_marL)
                        pPr.set('indent', str(-int(task_marL)))
                    else:
                        # 普通段落缺少 marL 时，使用模板的默认左边界，而不是
                        # 借用同一单元格中任务段落的缩进。
                        pPr.set('marL', paragraph_marL)
                        pPr.set('indent', '0')
                    
                    # 分配 tasks：每段落固定一个任务项
                    # 每个 • 独占一个段落，确保悬挂缩进正确生效：
                    # • 任务描述文字内容       ← 首行: marL+indent=0
                    #   任务描述换行文字       ← 续行: marL（与 company/role 等文字左对齐）
                    cell_replacements = dict(temp_replacements)
                    for tp in tasks_placeholders:
                        if tp in paragraph.text:
                            tp_para_seen[tp] = tp_para_seen.get(tp, 0) + 1
                            
                            if tp not in tasks_exhausted and tp in tasks_pool and tasks_pool[tp]:
                                # 每段落只放一项，不再用 \n 合并剩余项到末段
                                cell_replacements[tp] = tasks_pool[tp].pop(0)
                                if not tasks_pool[tp]:
                                    tasks_exhausted.add(tp)
                            else:
                                cell_replacements[tp] = ''
                                tasks_exhausted.add(tp)
                    
                    SmartFillerService.replace_text_in_paragraph(paragraph, cell_replacements)

                    for run in paragraph.runs:
                        if run.text:
                            run.font.size = Pt(PageConstraints.BODY_FONT_SIZE_PT)
                    if not paragraph.text.strip():
                        continue
                    
                    font_size = PageConstraints.BODY_FONT_SIZE_PT
                    
                    text_height = SmartFillerService._estimate_text_height(
                        paragraph.text,
                        font_size,
                        cell_width,
                        line_spacing_factor=1.0 if module.name == 'work' else 1.2,
                    )
                    cell_total_height += text_height
                
                # 取所有列中段落总高度的最大值（内循环结束时检查）
                # Remove empty template paragraphs so every populated row uses the
                # same compact spacing, while keeping one paragraph for an empty cell.
                for empty_para in reversed(list(cell.text_frame.paragraphs)):
                    if not empty_para.text.strip() and len(cell.text_frame.paragraphs) > 1:
                        empty_para._p.getparent().remove(empty_para._p)

                if cell_total_height > max_cell_height:
                    max_cell_height = cell_total_height
            
            # 设置行高（+15pt安全余量，与 estimate_row_height 保持一致，防止文字重叠）
            final_height = max(
                max_cell_height + Pt(PageConstraints.ROW_SAFETY_MARGIN_PT),
                PageConstraints.MIN_ROW_HEIGHT,
            )
            SmartFillerService._set_row_height(current_row, final_height)
            
            # 单元格格式化：防止文字重叠
            for cell in current_row.cells:
                cell.text_frame.word_wrap = True
                # 垂直靠上对齐，避免文字在单元格中间悬空导致重叠
                cell.vertical_anchor = MSO_ANCHOR.TOP
                # 缩减默认单元格内边距（默认约 0.05in = 3.6pt），给文字更多空间
                try:
                    from pptx.util import Inches
                    tight_margin = Inches(0.02)
                    cell.margin_left = tight_margin
                    cell.margin_right = tight_margin
                    cell.margin_top = tight_margin
                    cell.margin_bottom = tight_margin
                except Exception:
                    pass  # 模板可能已锁定边距
        
        # Drop unused cloned template rows. Their original fixed heights are
        # a major source of blank space after a one-item project list.
        used_row_end = template_row_idx + (end_idx - start_idx)
        tbl = module.table._tbl
        for row in list(module.table.rows)[used_row_end:][::-1]:
            row_text = " ".join(cell.text.strip() for cell in row.cells)
            has_dynamic = any("{{" + module.name + "." in cell.text for cell in row.cells)
            if has_dynamic or not row_text:
                tbl.remove(row._tr)
        # ===== 特殊处理：对于不在 ARRAY_FIELDS 中的模块（如 skill），
        # 用全局 replacements 填充占位符 =====
        # 原因：技能模块模板使用 {{tech_skills}}、{{lang_skills}} 等来自
        # FIELD_MAPPING 的全局占位符（而非 ARRAY_FIELDS 的索引占位符），
        # 这些占位符在数据循环中被跳过（temp_replacements 为空），
        # 因此需要在这里显式应用替换，否则后续清理会将其全部置空。
        if module.name not in ARRAY_FIELDS:
            for row in module.table.rows:
                for cell in row.cells:
                    for paragraph in cell.text_frame.paragraphs:
                        SmartFillerService.replace_text_in_paragraph(paragraph, replacements)

        # 清理残留的跨模块占位符（如项目表格中模板残余的 {{work.tasks}} 等）
        # 注意：占位符可能被 split 到多个 run 中（如 run[0]='{{', run[1]='work.tasks', run[2]='}}'），
        # 因此不能在单个 run 级别用 regex 匹配，而是要先用 paragraph.text 提取占位符，再调用
        # replace_text_in_paragraph() 处理（该方法有 fallback 逻辑合并多 run 文本）。
        for row in module.table.rows:
            for cell in row.cells:
                for paragraph in cell.text_frame.paragraphs:
                    full_text = paragraph.text
                    if '{{' in full_text and '}}' in full_text:
                        # 提取所有 {{...}} 占位符并构建清理替换字典
                        placeholders = re.findall(r'\{\{[\w.]+\}\}', full_text)
                        if placeholders:
                            cleanup_dict = {p: '' for p in placeholders}
                            SmartFillerService.replace_text_in_paragraph(paragraph, cleanup_dict)
        
        # 更新模块高度（先更新表格自身高度，再通过_update_boundary统一
        # 计算整个模块的top/bottom/height，避免忽略标题与表格之间的偏移量）
        new_height = 0
        for row in module.table.rows:
            if row.height:
                new_height += row.height
            else:
                new_height += int(PageConstraints.MIN_ROW_HEIGHT.pt * 12700)
        
        module.shape.height = new_height
        module._update_boundary()
    
    @staticmethod
    def _set_row_height(row, height_pt):
        """设置行高
        
        注意：height_pt 可能是 pptx.util.Pt/Length 对象，也可能因为两个 Length
        相加后被 Python 降级为普通 int（Length 相加返回 int 而非子类）。
        无论哪种情况，其数值本身都已经是 EMU（Length 内部就以 EMU 存储），
        因此这里直接转换为 int 写入即可，不需要再乘以 12700。
        """
        try:
            row.height = int(height_pt)
        except Exception:
            pass
    
    @staticmethod
    def move_module_down(module: ModuleInfo, distance: int):
        """向下移动模块（支持包含标题的模块）"""
        module.move_down(distance)
    
    @staticmethod
    def check_and_adjust_spacing(modules: List[ModuleInfo]) -> List[ModuleInfo]:
        """
        检查并调整模块间距，确保恰好为1cm（±1mm误差）
        
        参数:
            modules: 模块列表
            
        返回:
            调整后的模块列表
        """
        if len(modules) < 2:
            return modules
        
        print(f"   📐 调整模块间距...")
        
        for i in range(len(modules) - 1):
            current = modules[i]
            next_mod = modules[i + 1]
            
            # 确保边界是最新的
            current._update_boundary()
            next_mod._update_boundary()
            
            current_spacing = next_mod.top - current.bottom
            
            has_title = " (有标题)" if current.title_shape else ""
            next_has_title = " (有标题)" if next_mod.title_shape else ""
            
            if current_spacing > PageConstraints.MODULE_SPACING + 12700:  # 允许1mm误差
                # 间距过大，上移后续模块
                move_distance = current_spacing - PageConstraints.MODULE_SPACING
                print(f"   🔧 '{current.name}'{has_title}和'{next_mod.name}'{next_has_title}间距过大: "
                      f"{PageConstraints.emu_to_cm(current_spacing):.2f}cm → "
                      f"{PageConstraints.emu_to_cm(PageConstraints.MODULE_SPACING):.2f}cm")
                
                for j in range(i + 1, len(modules)):
                    SmartFillerService.move_module_down(modules[j], -move_distance)
            
            elif current_spacing < PageConstraints.MODULE_SPACING - 12700:
                # 间距过小，下移后续模块
                move_distance = PageConstraints.MODULE_SPACING - current_spacing
                print(f"   🔧 '{current.name}'{has_title}和'{next_mod.name}'{next_has_title}间距过小: "
                      f"{PageConstraints.emu_to_cm(current_spacing):.2f}cm → "
                      f"{PageConstraints.emu_to_cm(PageConstraints.MODULE_SPACING):.2f}cm")
                
                for j in range(i + 1, len(modules)):
                    SmartFillerService.move_module_down(modules[j], move_distance)
            
            else:
                print(f"   ✅ '{current.name}'{has_title}和'{next_mod.name}'{next_has_title}间距正常: "
                      f"{PageConstraints.emu_to_cm(current_spacing):.2f}cm")
        
        return modules
    
    @staticmethod
    def get_company_table(slide):
        """获取公司表格"""
        for shape in slide.shapes:
            if shape.has_table:
                table_text = ""
                for row in shape.table.rows:
                    for cell in row.cells:
                        table_text += cell.text
                if "IAV" in table_text and "Building" in table_text:
                    return shape
        return None
    
    @staticmethod
    def check_overlap_with_company_table(slide, company_table) -> bool:
        """检查是否与公司表格重叠"""
        if not company_table:
            return False
        
        company_top = company_table.top
        max_content_bottom = 0
        
        for shape in slide.shapes:
            if shape == company_table:
                continue
            
            # 检查是否是公司表格
            is_company = False
            if shape.has_table:
                text = ""
                for row in shape.table.rows:
                    for cell in row.cells:
                        text += cell.text
                if "IAV" in text and "Building" in text:
                    is_company = True
            
            if not is_company:
                bottom = shape.top + (shape.height or 0)
                if bottom > max_content_bottom:
                    max_content_bottom = bottom
        
        has_overlap = max_content_bottom > company_top
        
        if has_overlap:
            print(f"   ⚠️  检测到重叠:")
            print(f"      - 最后内容底部: {PageConstraints.emu_to_cm(max_content_bottom):.2f}cm")
            print(f"      - 公司表格顶部: {PageConstraints.emu_to_cm(company_top):.2f}cm")
        else:
            print(f"   ✅ 无重叠:")
            print(f"      - 最后内容底部: {PageConstraints.emu_to_cm(max_content_bottom):.2f}cm")
            print(f"      - 公司表格顶部: {PageConstraints.emu_to_cm(company_top):.2f}cm")
        
        return has_overlap
    
    @staticmethod
    def fill_module_data_simple(module: ModuleInfo, data_array: List[Dict], replacements: Dict[str, str]):
        """简化的模块填充方法 - 直接使用fill_module_data"""
        if not module.is_table:
            # 文本模块 - 直接替换占位符
            if hasattr(module.shape, 'text_frame'):
                for paragraph in module.shape.text_frame.paragraphs:
                    SmartFillerService.replace_text_in_paragraph(paragraph, replacements)
            return
        
        # 表格模块
        if not data_array:
            return
        
        # 使用fill_module_data方法
        SmartFillerService.fill_module_data(module, data_array, replacements, 0, len(data_array))
    
    @staticmethod
    def calculate_module_height(module: ModuleInfo) -> int:
        """计算模块的实际高度"""
        return module.shape.height or module.height
    
    @staticmethod
    def get_value_from_path(data: Dict[str, Any], path: str) -> Any:
        """从数据字典获取值"""
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
        """替换段落文本"""
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
                        run.text = run.text.replace(placeholder, str(value), 1)
                        replaced = True
        
        remaining_text = paragraph.text
        if any(
            placeholder in remaining_text for placeholder in replacements
        ):
            new_text = remaining_text
            for placeholder, value in replacements.items():
                new_text = new_text.replace(placeholder, str(value), 1)
            
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
            
            replaced = new_text != remaining_text or replaced

        if '{{lang_skills_level}}' in full_text and not replacements.get('{{lang_skills_level}}'):
            for match in reversed(list(re.finditer(r'\s*[（(]\s*[）)]', paragraph.text))):
                offset = 0
                for run in paragraph.runs:
                    end = offset + len(run.text)
                    left, right = max(0, match.start() - offset), min(len(run.text), match.end() - offset)
                    if left < right:
                        run.text = run.text[:left] + run.text[right:]
                    offset = end
        return replaced

    @staticmethod
    def _clean_education_text(value: Any) -> str:
        """Remove extraction notes and school ranking annotations from education fields."""
        if value is None:
            return ''
        text = re.sub(r'\*+', '', str(value)).replace('\r', ' ').replace('\n', ' ')
        if re.search(r'context\s+information', text, re.IGNORECASE):
            return ''

        # Ranking labels such as (211/985), [985], or Chinese full-width variants
        # are metadata, not part of the school name.
        text = re.sub(
            r'\s*[\(（\[【][^\)）\]】]*(?:211|985)[^\)）\]】]*[\)）\]】]',
            '', text, flags=re.IGNORECASE
        )
        text = re.sub(r'(?<!\w)(?:211\s*[/／]\s*985|985\s*[/／]\s*211)(?!\w)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'(?<!\w)(?:211|985)(?!\w)', '', text, flags=re.IGNORECASE)
        text = re.sub(r'^\s*(?:major|专业)\s*[:：]\s*', '', text, flags=re.IGNORECASE)
        text = re.sub(r'\s{2,}', ' ', text)
        return text.strip(' -–—,，;；:：|')

    @staticmethod
    def _normalize_education_entries(resume_dict: Dict[str, Any]) -> None:
        """Keep education output limited to period, school, degree, and major."""
        from app.schemas.education import normalize_degree

        cleaned_entries = []
        for item in resume_dict.get('education') or []:
            if not isinstance(item, dict):
                continue
            cleaned = {
                field: SmartFillerService._clean_education_text(item.get(field))
                for field in ('period', 'school', 'degree', 'major')
            }
            cleaned["degree"] = normalize_degree(cleaned["degree"])
            if any(cleaned.values()):
                cleaned_entries.append(cleaned)
        resume_dict['education'] = cleaned_entries

    @staticmethod
    def build_replacements(resume_dict: Dict[str, Any]) -> Dict[str, str]:
        """构建替换字典"""
        replacements = {}
        
        for placeholder, data_path in FIELD_MAPPING.items():
            value = SmartFillerService.get_value_from_path(resume_dict, data_path)
            replacements[placeholder] = str(value) if value else ''

        # Used for language-aware fallback labels in optional fields.
        replacements['{{language}}'] = str(resume_dict.get('language') or '')
        
        for array_name, config in ARRAY_FIELDS.items():
            data_array = resume_dict.get(config['data_key'], [])
            for field_suffix in config['template']:
                replacements.setdefault(
                    f'{{{{{array_name}.{field_suffix}}}}}', ''
                )
            for i in range(len(data_array)):
                for field_suffix, path_template in config['template'].items():
                    placeholder = f'{{{{{array_name}.{field_suffix}}}}}'
                    placeholder_with_index = f'{{{{{array_name}{i}.{field_suffix}}}}}'
                    
                    data_path = path_template.format(index=i)
                    value = SmartFillerService.get_value_from_path(resume_dict, data_path)
                    
                    replacements[placeholder_with_index] = str(value) if value else ''
                    if i == 0:
                        replacements[placeholder] = str(value) if value else ''
        
        if resume_dict.get('anonymized_name'):
            replacements['{{name}}'] = resume_dict['anonymized_name']
        
        return replacements
    
    @staticmethod
    def _determine_template_id(resume_data: ResumeData, 
                              template_type: Optional[TemplateType] = None,
                              orientation: str = 'vertical') -> str:
        """确定模板ID"""
        if template_type:
            if template_type not in TEMPLATE_CONFIG:
                raise ValueError(f'无效的模板类型: {template_type}')
            return template_type.value
        
        try:
            orient_enum = Orientation(orientation.lower())
        except ValueError:
            raise ValueError(f'无效的模板方向: {orientation}')
        
        language = resume_data.language or 'CN'
        if language not in ORIENTATION_TO_TEMPLATE:
            raise ValueError(f'不支持的语言: {language}')
        
        return ORIENTATION_TO_TEMPLATE[language][orient_enum].value
    
    @staticmethod
    def _prepare_output_directory():
        """准备输出目录"""
        os.makedirs(SmartFillerService.OUTPUT_DIR, exist_ok=True)
        if not os.access(SmartFillerService.OUTPUT_DIR, os.W_OK):
            raise PermissionError(f'没有写入权限: {SmartFillerService.OUTPUT_DIR}')
    
    @staticmethod
    def _load_presentation(template_id: str) -> Presentation:
        """加载Presentation"""
        template_path = SmartFillerService.get_template_path(template_id)
        if not os.path.exists(template_path):
            raise FileNotFoundError(f'模板文件不存在: {template_path}')
        
        try:
            return Presentation(template_path)
        except Exception as e:
            raise Exception(f'模板文件加载失败: {str(e)}')
    
    @staticmethod
    def fill_template(
        resume_data: ResumeData,
        template_type: Optional[TemplateType] = None,
        orientation: str = 'vertical',
        generate_pdf: bool = True,
    ) -> dict:
        """
        完整重构的PPT填充
        
        实现所有需求:
        1. 正确定义页面可输入范围
        2. 创建新页面并清理内容
        3. 模块间距≤1cm
        4. 智能分页
        5. 最终重叠检查
        6. 自动命名: IAV_{anonymized_name}_{position}_Resume_{language}
        7. 同时生成 PPTX + PDF
        
        Returns:
            dict: {"pptx_path": str, "pdf_path": str|None, "filename": str}
        """
        try:
            if not resume_data:
                raise ValueError('简历数据不能为空')
            
            resume_dict = resume_data.model_dump()
            SmartFillerService._normalize_education_entries(resume_dict)
            
            # 确定模板
            template_id = SmartFillerService._determine_template_id(
                resume_data, template_type, orientation
            )
            
            # 准备输出目录
            SmartFillerService._prepare_output_directory()
            
            # 加载模板
            prs = SmartFillerService._load_presentation(template_id)
            
            # 构建替换字典
            replacements = SmartFillerService.build_replacements(resume_dict)
            # Remove empty skill paragraphs before measuring pagination.
            SmartFillerService._cleanup_empty_skill_labels(prs, replacements)
            
            print("=" * 70)
            print("修复的PPT填充服务")
            print("=" * 70)
            
            # ========== 第一步：收集所有模块并准备数据 ==========
            print(f"\n📋 第一步：收集模块和准备数据...")
            
            # 收集所有模块
            all_modules = SmartFillerService.collect_all_modules(prs)
            print(f"   🔍 找到{len(all_modules)}个模块: {[m.name for m in all_modules]}")
            
            # 为每个模块准备数据
            module_data_map = SmartFillerService._prepare_module_data(resume_dict, all_modules)
            
            # ========== 第二步：填充非表格字段 ==========
            print(f"\n📝 第二步：填充非表格字段...")
            SmartFillerService._fill_non_table_fields(prs, replacements)
            
            # ========== 第三步：找到并保存公司表格 ==========
            print(f"\n🏢 第三步：保存公司表格...")
            (original_company_table, original_company_table_element, 
             original_company_table_top, company_table_slide_idx) = SmartFillerService._find_and_save_company_table(prs)
            
            # 删除所有页面的公司表格
            if original_company_table:
                print(f"   🧹 移除公司表格以便填充...")
                SmartFillerService._remove_company_table(prs)
            
            # ========== 第四步：智能分页填充 ==========
            print(f"\n🔄 第四步：智能分页填充...")
            SmartFillerService._smart_pagination_fill(prs, all_modules, module_data_map, replacements)

            # Recompute boundaries from the final cloned tables and move later
            # modules after any row-height growth. This is intentionally after
            # pagination because fill_module_data changes table geometry.
            SmartFillerService._adjust_module_spacing(prs)
            
            # ========== 第五步：调整模块间距（已在分页填充时处理）==========
            print(f"\n📐 第五步：模块间距已在分页填充时处理...")
            
            # ========== 第六步：处理公司表格 ==========
            # 公司表格必须始终位于整份简历的最后一页，且垂直位置固定为
            # original_company_table_top（模板中定义的24.13cm）。
            # 优先尝试放在分页填充后当前的最后一个内容页；
            # 只有当该页放不下（会与正文内容重叠）时，才新建一页并放在那一页的24.13cm处。
            # 无论哪种情况，公司表格有且仅有一份，且一定在最终PPT的最后一页。
            print(f"\n🏢 第六步：处理公司表格...")
            if original_company_table:
                last_page_idx = len(prs.slides) - 1
                last_content_bottom = SmartFillerService._calculate_last_content_bottom(prs.slides[last_page_idx])
                print(f"   📊 当前最后一页(第{last_page_idx + 1}页)内容底部: {PageConstraints.emu_to_cm(last_content_bottom):.2f}cm")
                print(f"   📊 公司表格固定位置: {PageConstraints.emu_to_cm(original_company_table_top):.2f}cm")
                
                # 检查固定位置是否会与该页正文内容重叠
                MIN_SPACING = PageConstraints.cm_to_emu(0.1)
                actual_spacing = original_company_table_top - last_content_bottom
                print(f"   📊 可用间距: {PageConstraints.emu_to_cm(actual_spacing):.2f}cm")
                
                if last_content_bottom <= 0 and last_page_idx > 0:
                    print("   ⚠️  最后一页没有正文内容，移除空白页并省略可选公司信息块")
                    SmartFillerService._remove_slide(prs, last_page_idx)
                elif actual_spacing < MIN_SPACING:
                    # 公司信息块是可选内容。最后一页没有足够空间时直接省略，
                    # 不为它单独创建页面，避免简历末尾出现只有页脚的空白页。
                    print(f"   ⚠️  最后一页空间不足，省略可选公司信息块")
                else:
                    print(f"   ✅ 空间足够，公司表格放在最后一页固定位置")
                    target_slide = prs.slides[last_page_idx]
                    target_slide.shapes._spTree.insert_element_before(original_company_table_element, 'p:extLst')
                    new_company_table = SmartFillerService.get_company_table(target_slide)
                    if new_company_table:
                        new_company_table.top = original_company_table_top
                        print(f"   ✅ 公司表格已放回，位置: {PageConstraints.emu_to_cm(original_company_table_top):.2f}cm")
            
            # ========== 第七步：清理空标题行 ==========
            print(f"\n🧹 第七步：清理空标题行...")
            SmartFillerService._cleanup_empty_skill_labels(prs, replacements)

            # ========== 第八步：字体格式归一化 ==========
            print(f"\n🎨 第八步：字体格式归一化...")
            SmartFillerService._normalize_page_numbers(prs)
            SmartFillerService._normalize_output_fonts(prs)

            # ========== 保存文件 (PPTX + PDF) ==========
            result = SmartFillerService._save_output_file(prs, resume_dict, template_id)
            
            # 如果不需要 PDF，清除 pdf_path
            if not generate_pdf:
                result["pdf_path"] = None
            
            return result
            
        except ValueError as e:
            raise e
        except FileNotFoundError as e:
            raise e
        except PermissionError as e:
            raise e
        except Exception as e:
            raise Exception(f'PPT填充失败: {str(e)}')
    
    @staticmethod
    def get_template_path(template_id: str) -> str:
        """获取模板文件路径"""
        if template_id not in TEMPLATE_CONFIG:
            raise ValueError(f"Unknown template: {template_id}")
        
        template_file = TEMPLATE_CONFIG[template_id]["file"]
        return os.path.join(SmartFillerService.TEMPLATES_DIR, template_file)
    
    @staticmethod
    def _prepare_module_data(resume_dict: dict, all_modules: list) -> dict:
        """准备模块数据"""
        processing_order = ['work', 'project', 'education', 'skill']
        module_data_map = {}
        
        for name in processing_order:
            data_array = resume_dict.get(name, [])
            
            if name == 'skill':
                # skill模块的模板行是"一行容纳所有技能占位符"（{{lang_skills}}、{{tech_skills}}等
                # 全局占位符），而不是像work/project/education那样每条数据克隆一行。
                # 因此这里只需要判断"是否有技能内容"，只应产生1个占位数据项，
                # 避免被误判为需要克隆出第2行（该行不在ARRAY_FIELDS中，克隆出的占位符
                # 无法被替换，会残留在输出中）。
                has_skill_content = bool(
                    resume_dict.get('lang_skills') or resume_dict.get('tech_skills')
                    or resume_dict.get('training_exp')
                )
                data_array = [{}] if has_skill_content else []
            
            module_data_map[name] = data_array
        
        for module in all_modules:
            if module.name in module_data_map:
                module.data_array = module_data_map[module.name]
        
        return module_data_map

    @staticmethod
    def _iter_nested_shapes(shapes):
        """Yield top-level shapes and every shape nested in a group."""
        for shape in shapes:
            yield shape
            if shape.shape_type == MSO_SHAPE_TYPE.GROUP:
                yield from SmartFillerService._iter_nested_shapes(shape.shapes)

    @staticmethod
    def _fill_non_table_fields(prs: Presentation, replacements: dict):
        """填充非表格字段"""
        for slide in prs.slides:
            for shape in SmartFillerService._iter_nested_shapes(slide.shapes):
                if not shape.has_table and hasattr(shape, 'text_frame'):
                    for paragraph in shape.text_frame.paragraphs:
                        SmartFillerService.replace_text_in_paragraph(paragraph, replacements)
    
    @staticmethod
    def _smart_pagination_fill(prs: Presentation, all_modules: list, module_data_map: dict, replacements: dict):
        """智能分页填充 - 核心逻辑

        按顺序：工作经历 → 项目经历 → 教育经历 → 职业技能
        对每个模块依次执行：
            尝试在当前页尽量多填数据 -> 判断是否溢出
                否 -> 模块填充完毕，继续本页填写下一个模块
                是 -> 切换到下一页，该模块剩余数据 + 后续所有模块都在新页面继续处理
        """
        print(f"\n🔄 开始智能分页填充（逐模块溢出判断）")
        
        processing_order = ['work', 'project', 'education', 'skill']
        
        # 保存每个模块的原始形状模板（用于复制到新页面）
        module_templates: Dict[str, ModuleInfo] = {}
        for module in all_modules:
            if module.name not in module_templates:
                module_templates[module.name] = module
        
        # 模板中所有"原本就存在"的页面（不仅仅是第一页！模板本身可能有多页，
        # 每一页都可能带有自己的一份模块占位符，例如第二页也可能有
        # project/education/skill的标题+表格）都只是用作"模板"，
        # 后续会在正确的位置重新插入填充好数据的副本。
        # 所以必须把这些原始形状从它们各自所在的页面移除，
        # 否则原始占位符文本会残留，并与新插入的、已填充数据的副本重叠。
        original_slide_count = len(prs.slides)
        first_module_top = None
        
        for slide_idx in range(original_slide_count):
            slide = prs.slides[slide_idx]
            slide_modules = SmartFillerService.collect_modules_on_slide(slide, slide_idx)
            
            if slide_idx == 0 and slide_modules:
                first_module_top = slide_modules[0].top
            
            for module in slide_modules:
                try:
                    if module.title_shape is not None:
                        slide.shapes._spTree.remove(module.title_shape.element)
                    slide.shapes._spTree.remove(module.shape.element)
                except Exception:
                    pass
        
        if first_module_top is None:
            first_module_top = PageConstraints.REGULAR_PAGE_TOP
        
        # 各模块剩余待填充数据
        module_remaining_data = {
            name: list(module_data_map.get(name, [])) for name in processing_order
        }
        
        current_slide_idx = 0
        current_y = first_module_top
        page_has_content = False
        last_module_on_page = None
        
        current_module_idx = 0
        while current_module_idx < len(processing_order):
            module_name = processing_order[current_module_idx]
            remaining_data = module_remaining_data.get(module_name, [])
            
            if not remaining_data:
                current_module_idx += 1
                continue
            
            module_template = module_templates.get(module_name)
            if not module_template:
                current_module_idx += 1
                continue
            
            print(f"\n   📦 处理模块: {module_name}, 剩余{len(remaining_data)}条数据")
            
            # 确保当前页面存在
            if current_slide_idx >= len(prs.slides):
                new_slide = SmartFillerService.create_new_page(prs, 0)
                current_slide_idx = len(prs.slides) - 1
                current_y = PageConstraints.REGULAR_PAGE_TOP
                page_has_content = False
                last_module_on_page = None
            
            current_slide = prs.slides[current_slide_idx]
            page_top, page_bottom = SmartFillerService.get_page_constraints(
                current_slide_idx, len(prs.slides) + 10
            )
            print(f"   📄 当前页面: {current_slide_idx + 1}，位置: {PageConstraints.emu_to_cm(current_y):.2f}cm")
            print(f"   📐 页面范围: {PageConstraints.emu_to_cm(page_top):.2f}cm - {PageConstraints.emu_to_cm(page_bottom):.2f}cm")
            
            # 计算表格实际起始位置（考虑标题偏移），估算当前页最多能放多少条数据
            # 使用安全余量抵消高度估算与实际渲染之间的误差，避免内容真正溢出页面
            SAFETY_MARGIN = PageConstraints.cm_to_emu(0.3)
            effective_page_bottom = page_bottom - SAFETY_MARGIN
            
            title_table_offset = 0
            if module_template.title_shape and last_module_on_page != module_name:
                title_table_offset = module_template.shape.top - module_template.title_shape.top
            table_start_y = current_y + title_table_offset

            max_fit, overflow_idx = SmartFillerService.calculate_pagination_for_module(
                module_template, remaining_data, replacements, table_start_y, page_top, effective_page_bottom
            )
            
            if max_fit == 0:
                available_height = effective_page_bottom - table_start_y
                allow_partial_page_split = (
                    not page_has_content
                    or (
                        module_name in ('work', 'project')
                        and available_height >= PageConstraints.cm_to_emu(3)
                    )
                )
                if allow_partial_page_split:
                    split_items = SmartFillerService._split_oversized_item(
                        module_template,
                        remaining_data[0],
                        replacements,
                        available_height,
                    )
                    if len(split_items) > 1:
                        split_fit, _ = SmartFillerService.calculate_pagination_for_module(
                            module_template,
                            split_items,
                            replacements,
                            table_start_y,
                            page_top,
                            effective_page_bottom,
                        )
                        if split_fit > 0:
                            remaining_data = split_items + remaining_data[1:]
                            module_remaining_data[module_name] = remaining_data
                            continue
                if not page_has_content:
                    # Non-task content itself is oversized; advance defensively.
                    max_fit = 1

            if max_fit == 0:
                # 当前页放不下一条，换到下一页重试同一模块
                print(f"   ⚠️  当前页放不下，换下一页")
                current_slide_idx += 1
                current_y = PageConstraints.REGULAR_PAGE_TOP
                page_has_content = False
                last_module_on_page = None
                continue
            
            # 正式复制模块并填充能放下的数据
            new_module = SmartFillerService._copy_module_to_slide_at_position(
                module_template,
                current_slide,
                current_y,
                include_title=last_module_on_page != module_name,
            )
            if not new_module:
                current_module_idx += 1
                continue
            
            page_data = remaining_data[:max_fit]
            SmartFillerService.fill_module_data(new_module, page_data, replacements, 0, len(page_data))
            page_has_content = True
            last_module_on_page = module_name
            
            # fill_module_data内部已经通过_update_boundary()正确计算了
            # 包含标题偏移在内的模块top/bottom/height，这里无需重复计算
            
            print(f"   ✅ 放入{len(page_data)}条数据，模块位置: "
                  f"{PageConstraints.emu_to_cm(new_module.top):.2f}cm - {PageConstraints.emu_to_cm(new_module.bottom):.2f}cm")
            
            module_remaining_data[module_name] = remaining_data[max_fit:]
            
            if len(module_remaining_data[module_name]) > 0:
                # Try the next item in the remaining space. If it still cannot fit,
                # the next loop will split it or advance to a new page.
                print(f"   ⚠️  模块 '{module_name}' 溢出，剩余{len(module_remaining_data[module_name])}条，继续利用本页剩余空间")
                current_y = new_module.bottom + PageConstraints.MODULE_SPACING
                # 不推进 current_module_idx，下一轮循环继续处理同一模块的剩余数据
            else:
                # 该模块填充完毕，继续本页填写下一个模块
                print(f"   ✅ 模块 '{module_name}' 填充完毕，继续下一个模块")
                current_y = new_module.bottom + PageConstraints.MODULE_SPACING
                current_module_idx += 1
    
    @staticmethod
    def _copy_module_to_slide_at_position(
        module: ModuleInfo,
        target_slide,
        top: int,
        include_title: bool = True,
    ) -> Optional[ModuleInfo]:
        """复制模块到指定位置"""
        title_shape = module.title_shape if include_title else None
        shape = module.shape
        
        # 记录标题和表格的相对偏移，保持复制后二者的相对位置关系
        title_table_offset = shape.top - title_shape.top if title_shape else 0
        
        # 复制标题
        new_title_shape = None
        if title_shape:
            new_title_element = SmartFillerService._clone_shape_element(
                title_shape, target_slide
            )
            target_slide.shapes._spTree.insert_element_before(new_title_element, 'p:extLst')
            for shape_obj in target_slide.shapes:
                if shape_obj.element is new_title_element:
                    new_title_shape = shape_obj
                    break
        
        # 复制主形状（表格）
        new_shape_element = SmartFillerService._clone_shape_element(
            shape, target_slide
        )
        target_slide.shapes._spTree.insert_element_before(new_shape_element, 'p:extLst')
        
        new_shape = None
        for shape_obj in target_slide.shapes:
            if shape_obj.element is new_shape_element:
                new_shape = shape_obj
                break
        
        if not new_shape:
            return None
        
        # 设置位置
        if new_title_shape:
            new_title_shape.top = top
            new_shape.top = top + title_table_offset
        else:
            new_shape.top = top
        
        # 创建新模块信息
        new_module = ModuleInfo(
            module.name,
            new_shape,
            new_shape.table if new_shape.has_table else None,
            target_slide,
            new_title_shape
        )
        
        return new_module
    
    @staticmethod
    def _fill_modules_simple(prs: Presentation, module_data_map: dict, replacements: dict):
        """简化填充模块，保持原始布局"""
        for slide_idx, slide in enumerate(prs.slides):
            page_top, page_bottom = SmartFillerService.get_page_constraints(
                slide_idx, len(prs.slides)
            )
            print(f"\n📄 处理第{slide_idx + 1}页")
            print(f"   📐 页面范围: {PageConstraints.emu_to_cm(page_top):.2f}cm - {PageConstraints.emu_to_cm(page_bottom):.2f}cm")
            
            slide_modules = SmartFillerService.collect_modules_on_slide(slide, slide_idx)
            slide_modules.sort(key=lambda m: m.top)
            
            for module in slide_modules:
                module_name = module.name
                data_array = module_data_map.get(module_name, [])
                
                if not data_array:
                    print(f"   ⏭️  模块'{module_name}'无数据，跳过")
                    continue
                
                print(f"\n   📦 处理模块: {module_name}, {len(data_array)}条数据")
                print(f"   📍 原始位置: {PageConstraints.emu_to_cm(module.top):.2f}cm")
                
                SmartFillerService.fill_module_data_simple(module, data_array, replacements)
                
                # fill_module_data内部已通过_update_boundary()正确计算了模块位置
                
                print(f"   ✅ 模块填充完成，新高度: {PageConstraints.emu_to_cm(module.height):.2f}cm")
                print(f"   📊 模块位置: {PageConstraints.emu_to_cm(module.top):.2f}cm - {PageConstraints.emu_to_cm(module.bottom):.2f}cm")
    
    @staticmethod
    def _find_and_save_company_table(prs: Presentation) -> tuple:
        """查找并保存公司表格信息"""
        original_company_table = None
        original_company_table_element = None
        original_company_table_top = 0
        company_table_slide_idx = -1
        
        for slide_idx, slide in enumerate(prs.slides):
            ct = SmartFillerService.get_company_table(slide)
            if ct:
                original_company_table = ct
                original_company_table_element = deepcopy(ct.element)
                original_company_table_top = ct.top
                company_table_slide_idx = slide_idx
                print(f"   🏢 找到公司表格在第{slide_idx + 1}页")
                print(f"      位置: {PageConstraints.emu_to_cm(original_company_table_top):.2f}cm")
                break
        
        return (original_company_table, original_company_table_element, 
                original_company_table_top, company_table_slide_idx)
    
    @staticmethod
    def _calculate_last_content_bottom(slide) -> int:
        """计算指定单个页面内正文内容（不含公司表格）的最大底部位置
        
        注意：只检查传入的这一页，不能跨页比较——不同页面的坐标
        都是相对于各自页面的0-27.94cm范围，跨页比较top/bottom没有意义。
        """
        last_content_bottom = 0
        
        for shape in slide.shapes:
            is_company = False
            if shape.has_table:
                text = ""
                for row in shape.table.rows:
                    for cell in row.cells:
                        text += cell.text
                if "IAV" in text and "Building" in text:
                    is_company = True
            
            if not is_company:
                has_content = False
                if shape.has_table:
                    # 页脚公司信息块保留模板字号，不纳入正文统一字号规则。
                    has_content = True
                elif shape.has_text_frame:
                    text = shape.text.strip()
                    if text and "单击" not in text and "Click to" not in text and len(text) > 5:
                        has_content = True
                
                if has_content:
                    bottom = shape.top + (shape.height or 0)
                    if bottom > last_content_bottom:
                        last_content_bottom = bottom
        
        return last_content_bottom
    
    @staticmethod
    def _remove_slide(prs: Presentation, slide_idx: int) -> None:
        """Remove a generated trailing slide without leaving a dangling relationship."""
        if slide_idx < 0 or slide_idx >= len(prs.slides):
            return
        slide_id = prs.slides._sldIdLst[slide_idx]
        prs.part.drop_rel(slide_id.rId)
        del prs.slides._sldIdLst[slide_idx]

    @staticmethod
    def _remove_company_table(prs: Presentation):
        """从所有页面移除公司表格"""
        for slide_idx, slide in enumerate(prs.slides):
            ct = SmartFillerService.get_company_table(slide)
            if ct:
                try:
                    slide.shapes._spTree.remove(ct.element)
                except Exception:
                    pass
    
    @staticmethod
    def _adjust_module_spacing(prs: Presentation):
        """调整所有页面的模块间距"""
        for slide_idx, slide in enumerate(prs.slides):
            modules = SmartFillerService.collect_modules_on_slide(slide, slide_idx)
            if modules:
                print(f"\n   📄 调整第{slide_idx + 1}页模块间距...")
                SmartFillerService.check_and_adjust_spacing(modules)
    
    @staticmethod
    def _insert_intermediate_page(prs: Presentation, company_table_slide_idx: int,
                                  original_company_table_element, original_company_table_top):
        """插入中间页面"""
        source_slide = prs.slides[0] if len(prs.slides) > 0 else prs.slides[-1]
        intermediate_slide = SmartFillerService._duplicate_slide_advanced(prs, source_slide)
        
        shapes_to_remove = []
        for shape in intermediate_slide.shapes:
            is_default = False
            if shape.has_text_frame:
                text = shape.text.strip()
                if not text or "单击" in text or "Click to" in text:
                    is_default = True
            if shape.has_table:
                is_default = True
            if is_default:
                shapes_to_remove.append(shape)
        
        for shape in reversed(shapes_to_remove):
            try:
                intermediate_slide.shapes._spTree.remove(shape.element)
            except Exception:
                pass
        
        content_slide_idx = company_table_slide_idx
        content_slide = prs.slides[content_slide_idx]
        
        content_shapes = []
        for shape in content_slide.shapes:
            has_content = False
            if shape.has_table:
                has_content = True
            elif shape.has_text_frame:
                text = shape.text.strip()
                if text and "单击" not in text and "Click to" not in text and len(text) > 5:
                    has_content = True
            if has_content:
                content_shapes.append(shape)
        
        content_shapes.sort(key=lambda s: s.top)
        
        current_y = PageConstraints.REGULAR_PAGE_TOP
        for shape in content_shapes:
            new_shape_element = SmartFillerService._clone_shape_element(
                shape, intermediate_slide
            )
            intermediate_slide.shapes._spTree.insert_element_before(new_shape_element, 'p:extLst')
            
            for new_shape in intermediate_slide.shapes:
                if new_shape.element is new_shape_element:
                    new_shape.top = current_y
                    current_y += (shape.height or 0) + PageConstraints.MODULE_SPACING
                    break
            
            try:
                content_slide.shapes._spTree.remove(shape.element)
            except Exception:
                pass
        
        print(f"   ✅ 已移动{len(content_shapes)}个形状到中间页面")
        
        last_slide = prs.slides[-1]
        last_slide.shapes._spTree.insert_element_before(original_company_table_element, 'p:extLst')
        new_company_table = SmartFillerService.get_company_table(last_slide)
        if new_company_table:
            new_company_table.top = original_company_table_top
            print(f"   ✅ 公司表格已放回第{len(prs.slides)}页，位置: {PageConstraints.emu_to_cm(original_company_table_top):.2f}cm")
    
    @staticmethod
    def _restore_company_table(prs: Presentation, company_table_slide_idx: int,
                              original_company_table_element, original_company_table_top):
        """恢复公司表格到原位置"""
        last_slide = prs.slides[company_table_slide_idx] if company_table_slide_idx >= 0 else prs.slides[-1]
        last_slide.shapes._spTree.insert_element_before(original_company_table_element, 'p:extLst')
        new_company_table = SmartFillerService.get_company_table(last_slide)
        if new_company_table:
            new_company_table.top = original_company_table_top
            print(f"   ✅ 公司表格已放回，位置: {PageConstraints.emu_to_cm(original_company_table_top):.2f}cm")

    @staticmethod
    def _cleanup_empty_skill_labels(prs: Presentation, replacements: dict):
        """清理 skill 表格中值为空的标题行

        模板中 skill/qualification 表格可能包含：
          Language: {{lang_skills}} ({{lang_skills_level}})
          Technical skills: {{tech_skills}}
          Training experience: {{training_exp}}

        替换后，若值为空则变成 "Language:  ()" 或 "Technical skills: "
        需要将这些行连同标题一起删除。
        """
        # 中英文标签模式
        label_patterns = [
            (r'Language(?:\s+Skills?)?\s*[:：]\s*(?:[（(]\s*[)）])?\s*$', 'lang_skills'),
            (r'语言(?:技能)?\s*[:：]\s*(?:[（(]\s*[)）])?\s*$', 'lang_skills'),
            (r'Technical\s+skills?\s*:\s*$', 'tech_skills'),
            (r'技术技能\s*[:：]\s*$', 'tech_skills'),
            (r'Training\s+experience\s*:\s*$', 'training_exp'),
            (r'培训经历\s*[:：]\s*$', 'training_exp'),
        ]

        # 检查哪些字段为空
        empty_fields = set()
        for field in ['lang_skills', 'tech_skills', 'training_exp']:
            # 检查 replacement 字典中的值
            val = replacements.get(f'{{{{{field}}}}}', '')
            if not val or not val.strip():
                empty_fields.add(field)

        if not empty_fields:
            print(f"   ✅ 所有技能字段均有值，无需清理")
            return

        # 遍历所有页面的表格
        cleaned_count = 0
        for slide in prs.slides:
            for shape in slide.shapes:
                if not shape.has_table:
                    continue
                table = shape.table
                for row in list(table.rows):
                    removed = False
                    for cell in row.cells:
                        for paragraph in list(cell.text_frame.paragraphs):
                            text = paragraph.text
                            for placeholder, value in replacements.items():
                                text = text.replace(placeholder, str(value or ''))
                            empty_value = (
                                not re.sub(r'[\s()（）]', '', text)
                                and any('{{' + field + '}}' in paragraph.text for field in empty_fields)
                            )
                            if empty_value or any(field in empty_fields and re.fullmatch(
                                pattern, text.strip(), re.IGNORECASE
                            ) for pattern, field in label_patterns):
                                paragraph._p.getparent().remove(paragraph._p)
                                removed = True
                                cleaned_count += 1
                        if not cell.text_frame.paragraphs:
                            cell.text_frame.add_paragraph()
                    # A row can contain several skill fields; retain its nonempty cells.
                    if removed and not any(cell.text.strip() for cell in row.cells):
                        table._tbl.remove(row._tr)

        if cleaned_count > 0:
            print(f"   🧹 已清理 {cleaned_count} 个空标题行")
        else:
            print(f"   ✅ 未发现需要清理的空标题行")

    @staticmethod
    def _normalize_paragraph_format(paragraph) -> None:
        """Use one compact paragraph rhythm across generated text frames."""
        try:
            paragraph.space_before = Pt(0)
            paragraph.space_after = Pt(0)
            paragraph.line_spacing = 1.0
        except Exception:
            pass

    @staticmethod
    def _set_arial_font(run) -> bool:
        """Set the visible run and its East Asian/Latin font faces to Arial."""
        changed = run.font.name != 'Arial'
        run.font.name = 'Arial'
        try:
            rpr = run._r.get_or_add_rPr()
            namespace = 'http://schemas.openxmlformats.org/drawingml/2006/main'
            for tag in ('latin', 'ea', 'cs'):
                element = rpr.find(f'{{{namespace}}}{tag}')
                if element is None:
                    element = etree.SubElement(rpr, f'{{{namespace}}}{tag}')
                if element.get('typeface') != 'Arial':
                    element.set('typeface', 'Arial')
                    changed = True
        except Exception:
            pass
        return changed

    @staticmethod
    def _normalize_page_numbers(prs: Presentation) -> None:
        """Keep static total-page text in masters in sync after pagination."""
        total_pages = len(prs.slides)
        total_pattern = re.compile(r'\(\s*\d+\s*\)')

        # The reference templates store "Page <slide number> (2)" in the
        # slide master.  The slide number itself is a PowerPoint field; only
        # the static total-page suffix needs updating.
        for master in prs.slide_masters:
            for shape in master.shapes:
                if not getattr(shape, 'has_text_frame', False):
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        if run.text and total_pattern.search(run.text):
                            run.text = total_pattern.sub(f'({total_pages})', run.text)
                        SmartFillerService._set_arial_font(run)

        # Some templates duplicate footer text in a slide layout.  Normalize
        # those runs as well so the generated PPTX and converted PDF agree.
        for layout in prs.slide_layouts:
            for shape in layout.shapes:
                if not getattr(shape, 'has_text_frame', False):
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    for run in paragraph.runs:
                        if run.text and total_pattern.search(run.text):
                            run.text = total_pattern.sub(f'({total_pages})', run.text)
                        SmartFillerService._set_arial_font(run)

    @staticmethod
    def _normalize_output_fonts(prs: Presentation):
        """字体格式归一化 - 确保输出PPT字体与参考效果一致

        基于参考CN PPT分析的标准格式:
          - 表格内容: +mn-lt 11pt (公司/角色名粗体，描述非粗体)
          - 非表格正文: 14pt (章节标题粗体)
          - 底部公司信息: Arial 10pt

        此方法作为安全网，确保即使模板字体不完整也能输出正确格式。
        """
        import re

        # 表格中"职责/任务描述"列的常见标签（正则匹配）
        TASK_LABEL_PATTERNS = [
            r'^(Tasks?\s*[:：]\s*)',
            r'^(职责\s*[:：]\s*)',
            r'^(Duties?\s*[:：]\s*)',
            r'^(Responsibilities?\s*[:：]\s*)',
        ]
        # 公司/角色行特征（粗体）
        BOLD_PATTERNS = [
            r'^[\u4e00-\u9fff\w\s&\(\)]+(?:有限)?(?:公司|科技|汽车|集团|技术|Ltd|Inc|Corp|Co\.)',
        ]

        fixed_count = 0
        for slide in prs.slides:
            company_table = SmartFillerService.get_company_table(slide)
            for shape in slide.shapes:
                # ---- 表格字体归一化 ----
                if shape.has_table:
                    # 页脚公司信息块保留模板字号，不纳入正文统一字号规则。
                    for row in shape.table.rows:
                        for cell in row.cells:
                            for para in cell.text_frame.paragraphs:
                                SmartFillerService._normalize_paragraph_format(para)
                                full_text = para.text.strip()
                                for run in para.runs:
                                    if SmartFillerService._set_arial_font(run):
                                        fixed_count += 1
                                    if not run.text.strip():
                                        continue
                                    cur_size = run.font.size
                                    cur_size_pt = cur_size / 12700 if cur_size else None

                                    # 表格内容统一 11pt（容差范围内修正）
                                    if not (company_table is not None and shape == company_table) and cur_size_pt != PageConstraints.BODY_FONT_SIZE_PT:
                                        run.font.size = Pt(PageConstraints.BODY_FONT_SIZE_PT)
                                        fixed_count += 1
                                for empty_para in reversed(list(cell.text_frame.paragraphs)):
                                    if not empty_para.text.strip() and len(cell.text_frame.paragraphs) > 1:
                                        empty_para._p.getparent().remove(empty_para._p)

                # ---- 非表格字段归一化 ----
                if shape.has_text_frame:
                    for para in shape.text_frame.paragraphs:
                        SmartFillerService._normalize_paragraph_format(para)
                        for run in para.runs:
                            if SmartFillerService._set_arial_font(run):
                                fixed_count += 1
                            if not run.text.strip():
                                continue
                            cur_size = run.font.size
                            cur_size_pt = cur_size / 12700 if cur_size else None

                            # 小字(9pt以下) → 11pt
                            if cur_size_pt and cur_size_pt < 9:
                                run.font.size = Pt(11)
                                fixed_count += 1

        # Headers/footers live on the master and are not exposed through
        # prs.slides, so apply the same font normalization to them explicitly.
        for master in prs.slide_masters:
            for shape in master.shapes:
                if not getattr(shape, 'has_text_frame', False):
                    continue
                for paragraph in shape.text_frame.paragraphs:
                    SmartFillerService._normalize_paragraph_format(paragraph)
                    for run in paragraph.runs:
                        if SmartFillerService._set_arial_font(run):
                            fixed_count += 1

        if fixed_count > 0:
            print(f"   🎨 已修正 {fixed_count} 处字体大小")
        else:
            print(f"   ✅ 字体格式无需修正")

    @staticmethod
    def _save_output_file(prs: Presentation, resume_dict: dict, template_id: str) -> dict:
        """
        保存输出文件 (PPTX + PDF)
        
        文件名规则: IAV_{anonymized_name}_{position}_Resume_{template_language}
        同时生成 PPTX 和 PDF 两个版本
        
        Returns:
            dict: {"pptx_path": str, "pdf_path": str|None, "filename": str}
        """
        # 文件名: IAV_{name}_{position}_Resume_{language}
        # name 不论 CN/EN 输出，统一使用英文格式: Mr./Ms.+姓氏拼音 (e.g. "Mr.Zhang")
        job_position = (
            resume_dict.get('job_position_en')
            or resume_dict.get('position_en')
            or resume_dict.get('job_position')
            or resume_dict.get('position', 'resume')
            or 'resume'
        )
        language = TEMPLATE_CONFIG.get(template_id, {}).get('language', 'CN')
        
        # 优先使用已存在的英文敬称格式
        anon_en = resume_dict.get('anonymized_name', '')
        if anon_en and (anon_en.startswith('Mr.') or anon_en.startswith('Ms.')):
            honorific_match = re.match(r'^(Mr\.|Ms\.)\s*([A-Za-z]+)', str(anon_en).strip())
            if honorific_match:
                name = f'{honorific_match.group(1)} {honorific_match.group(2).capitalize()}'
            else:
                name = str(anon_en).strip()
        else:
            # 从中文敬称 + 性别构建英文格式
            name_cn = resume_dict.get('anonymized_name_cn', '')
            gender = resume_dict.get('gender', 'male') or 'male'
            if name_cn and len(name_cn) >= 2:
                from app.services.anonymizer_service import AnonymizerService
                surname_pinyin = AnonymizerService._chinese_name_to_pinyin(name_cn[0])
                prefix = 'Ms.' if gender == 'female' else 'Mr.'
                name = f'{prefix} {surname_pinyin}'
            else:
                raw_name = str(resume_dict.get('name', 'output') or 'output').strip()
                if raw_name and '\u4e00' <= raw_name[0] <= '\u9fff':
                    from app.services.anonymizer_service import AnonymizerService
                    surname_pinyin = AnonymizerService._chinese_name_to_pinyin(raw_name[0])
                    prefix = 'Ms.' if gender == 'female' else 'Mr.'
                    name = f'{prefix} {surname_pinyin}'
                else:
                    name = raw_name
        
        safe_name = re.sub(r'[^A-Za-z0-9_.\- ]', '', str(name)).strip()
        safe_position = re.sub(r'[^a-zA-Z0-9\-\. ]', '', str(job_position))
        # 安全兜底：如果去除非ASCII字符后为空，使用'resume'
        safe_position = safe_position or 'resume'
        
        base_filename = f'IAV_{safe_name}_{safe_position}_Resume_{language}'
        date_stamp = datetime.now().strftime('%Y%m%d')
        output_filename = f'{base_filename}_{date_stamp}_{uuid4().hex[:12]}.pptx'
        
        output_path = os.path.join(SmartFillerService.OUTPUT_DIR, output_filename)
        
        # 保存 PPTX
        try:
            SmartFillerService._remove_dangling_shape_tags(prs)
            prs.save(output_path)
        except PermissionError:
            raise PermissionError(f'无法保存文件，请关闭已打开的PPT: {output_path}')
        except Exception as e:
            raise Exception(f'文件保存失败: {str(e)}')
        
        if not os.path.exists(output_path):
            raise Exception(f'文件创建失败: {output_path}')
        
        print(f"\n" + "=" * 70)
        print(f"✅ PPT填充完成!")
        print(f"📄 总页数: {len(prs.slides)}")
        print(f"📄 PPTX: {output_path}")
        
        # 生成 PDF
        pdf_path = None
        try:
            from .pdf_converter import PdfConverterService
            if PdfConverterService.is_available():
                pdf_path = PdfConverterService.convert_pptx_to_pdf(output_path)
                print(f"📄 PDF: {pdf_path}")
            else:
                print(f"⚠️ LibreOffice 未安装，跳过 PDF 生成")
        except Exception as e:
            print(f"⚠️ PDF 生成失败 (非致命): {e}")
        
        print("=" * 70)
        
        return {
            "pptx_path": output_path,
            "pdf_path": pdf_path,
            "filename": cv_download_filename(output_filename),
        }
    _RELATIONSHIP_ATTRIBUTE_NS = (
        "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
    )

    @staticmethod
    def _clone_shape_element(shape, target_slide):
        """Clone a shape and remap every OOXML relationship to the target slide.

        A raw deepcopy preserves r:id/r:embed values from the source slide but
        does not copy their relationships. PowerPoint then repairs the file and
        may remove the affected shapes. Remapping includes Office shape tags,
        images and hyperlinks.
        """
        element = deepcopy(shape.element)
        remapped = {}
        source_rels = shape.part.rels
        target_part = target_slide.part

        for node in element.iter():
            for attribute, old_rid in list(node.attrib.items()):
                if not attribute.startswith(
                    SmartFillerService._RELATIONSHIP_ATTRIBUTE_NS
                ):
                    continue
                # Some PowerPoint templates contain an optional relationship
                # attribute with an empty value. It is not a relationship
                # reference and must remain empty rather than being remapped.
                if not old_rid:
                    continue
                if old_rid not in source_rels:
                    raise ValueError(
                        f"Shape '{getattr(shape, 'name', '')}' references "
                        f"missing relationship {old_rid}"
                    )
                if old_rid not in remapped:
                    relationship = source_rels[old_rid]
                    if relationship.is_external:
                        new_rid = target_part.relate_to(
                            relationship.target_ref,
                            relationship.reltype,
                            is_external=True,
                        )
                    else:
                        new_rid = target_part.relate_to(
                            relationship.target_part,
                            relationship.reltype,
                        )
                    remapped[old_rid] = new_rid
                node.set(attribute, remapped[old_rid])
        return element

    @staticmethod
    def _remove_dangling_shape_tags(prs) -> int:
        """Remove only invisible Office tag metadata with missing relations.

        Missing relationships for visible content (pictures, hyperlinks, etc.)
        are never discarded because doing so would hide content loss.
        """
        relationship_ns = SmartFillerService._RELATIONSHIP_ATTRIBUTE_NS
        removed = 0
        for slide in prs.slides:
            valid_ids = set(slide.part.rels.keys())
            for node in list(slide.element.iter()):
                missing = {
                    value
                    for attribute, value in node.attrib.items()
                    if attribute.startswith(relationship_ns)
                    and value
                    and value not in valid_ids
                }
                if not missing:
                    continue
                if etree.QName(node).localname != "tags":
                    raise ValueError(
                        "PPTX visible content references missing relationships: "
                        + ", ".join(sorted(missing))
                    )
                parent = node.getparent()
                container = parent if parent is not None else node
                grandparent = container.getparent()
                if grandparent is None:
                    raise ValueError("Unable to remove dangling Office tag metadata")
                grandparent.remove(container)
                removed += 1
        return removed

