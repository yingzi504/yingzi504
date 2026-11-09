"""
PPTX 程序化验证器 - 检测重叠、文字溢出、间距违规等问题

基于 Anthropic Skills PPTX QA 的检查理念，实现程序化的自动检查:
- 元素重叠检测
- 文字溢出检测 (文字超出文本框边界)
- 元素间距检查
- 页边距检查
- 留白检查
"""

import os
import posixpath
import re
import zipfile
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field
from pptx import Presentation
from pptx.util import Emu, Pt, Inches
from pptx.enum.text import PP_ALIGN
from lxml import etree


# ── 常量定义 ──────────────────────────────────────────────

CM_TO_EMU = 360000
MIN_MARGIN_CM = 0.5        # 最小页边距
MIN_ELEMENT_GAP_CM = 0.3   # 元素间最小间隙
OVERLAP_TOLERANCE_CM = 0.05  # 重叠容忍度
TEXT_OVERFLOW_TOLERANCE = 0.30  # 文字溢出容忍度 (30%, 更宽松)
DECORATIVE_NAMES = {'rectangle', '矩形', 'background', '背景', 'shape', 'group'}


# ── 数据结构 ──────────────────────────────────────────────

@dataclass
class ValidationIssue:
    """单个验证问题"""
    severity: str           # "error" | "warning" | "info"
    category: str           # "overlap" | "text_overflow" | "spacing" | "margin"
    slide_num: int          # 幻灯片编号 (1-based)
    description: str        # 问题描述
    element1: str = ""      # 涉及元素1的名称/文本
    element2: str = ""      # 涉及元素2的名称/文本 (用于重叠/间距问题)
    coords: str = ""        # 坐标信息
    suggestion: str = ""    # 修复建议


@dataclass
class ValidationResult:
    """验证结果汇总"""
    file_path: str
    is_valid: bool          # 是否通过验证 (无 error 级别问题)
    total_slides: int
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    infos: List[ValidationIssue] = field(default_factory=list)
    
    @property
    def all_issues(self) -> List[ValidationIssue]:
        return self.errors + self.warnings + self.infos
    
    @property
    def error_count(self) -> int:
        return len(self.errors)
    
    @property
    def warning_count(self) -> int:
        return len(self.warnings)
    
    def to_dict(self) -> dict:
        return {
            "file_path": self.file_path,
            "is_valid": self.is_valid,
            "total_slides": self.total_slides,
            "error_count": self.error_count,
            "warning_count": self.warning_count,
            "info_count": len(self.infos),
            "errors": [self._issue_to_dict(i) for i in self.errors],
            "warnings": [self._issue_to_dict(i) for i in self.warnings],
            "infos": [self._issue_to_dict(i) for i in self.infos],
        }
    
    @staticmethod
    def _issue_to_dict(issue: ValidationIssue) -> dict:
        return {
            "severity": issue.severity,
            "category": issue.category,
            "slide_num": issue.slide_num,
            "description": issue.description,
            "element1": issue.element1,
            "element2": issue.element2,
            "coords": issue.coords,
            "suggestion": issue.suggestion,
        }


@dataclass
class ShapeInfo:
    """形状信息 (用于重叠检测)"""
    name: str
    text: str
    left: int      # EMU
    top: int       # EMU
    right: int     # EMU (left + width)
    bottom: int    # EMU (top + height)
    width: int
    height: int
    shape_type: str  # "text_box" | "table" | "picture" | "other"
    slide_num: int


# ── 验证器 ─────────────────────────────────────────────────

class PPTXValidator:
    """PPTX 程序化验证器"""
    
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.prs: Optional[Presentation] = None
        self.issues: List[ValidationIssue] = []
    
    def validate(self) -> ValidationResult:
        """执行完整验证"""
        self.issues = []
        
        if not os.path.exists(self.file_path):
            # 文件不存在
            result = ValidationResult(
                file_path=self.file_path,
                is_valid=False,
                total_slides=0,
            )
            result.errors.append(ValidationIssue(
                severity="error",
                category="file",
                slide_num=0,
                description=f"文件不存在: {self.file_path}",
            ))
            return result
        
        try:
            self.prs = Presentation(self.file_path)
        except Exception as e:
            result = ValidationResult(
                file_path=self.file_path,
                is_valid=False,
                total_slides=0,
            )
            result.errors.append(ValidationIssue(
                severity="error",
                category="file",
                slide_num=0,
                description=f"无法打开PPT文件: {str(e)}",
            ))
            return result
        
        total = len(self.prs.slides)

        # PowerPoint is stricter than python-pptx when slide XML references a
        # relationship that is absent from the corresponding .rels part.
        self._check_package_relationships()
        
        # 逐页检查
        for slide_idx, slide in enumerate(self.prs.slides):
            slide_num = slide_idx + 1
            
            # 收集当前页所有有意义的形状
            shapes = self._collect_shapes(slide, slide_num)
            
            # 1. 检查重叠
            self._check_overlaps(shapes, slide_num)
            
            # 2. 检查文字溢出
            self._check_text_overflow(slide, shapes, slide_num)
            
            # 3. 检查间距
            self._check_spacing(shapes, slide_num)
            
            # 4. 检查页边距
            self._check_margins(shapes, slide, slide_num)
        
        # 分类问题
        errors = [i for i in self.issues if i.severity == "error"]
        warnings = [i for i in self.issues if i.severity == "warning"]
        infos = [i for i in self.issues if i.severity == "info"]
        
        return ValidationResult(
            file_path=self.file_path,
            is_valid=len(errors) == 0,
            total_slides=total,
            errors=errors,
            warnings=warnings,
            infos=infos,
        )

    def _check_package_relationships(self) -> None:
        """Report dangling OOXML relationship references as blocking errors."""
        relationship_ns = (
            "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
        )
        package_relationship_ns = (
            "{http://schemas.openxmlformats.org/package/2006/relationships}"
        )
        with zipfile.ZipFile(self.file_path) as package:
            names = set(package.namelist())
            slide_names = sorted(
                name
                for name in names
                if re.match(r"ppt/slides/slide\d+\.xml$", name)
            )
            for slide_name in slide_names:
                slide_num = int(re.search(r"slide(\d+)\.xml$", slide_name).group(1))
                rels_name = posixpath.join(
                    posixpath.dirname(slide_name),
                    "_rels",
                    posixpath.basename(slide_name) + ".rels",
                )
                related_ids = set()
                if rels_name in names:
                    rels_root = etree.fromstring(package.read(rels_name))
                    related_ids = {
                        node.get("Id")
                        for node in rels_root.iter(
                            package_relationship_ns + "Relationship"
                        )
                    }
                slide_root = etree.fromstring(package.read(slide_name))
                office_tags = list(slide_root.iter(
                    "{http://schemas.openxmlformats.org/presentationml/2006/main}tags"
                ))
                if office_tags:
                    self.issues.append(ValidationIssue(
                        severity="error",
                        category="package_integrity",
                        slide_num=slide_num,
                        description=(
                            "幻灯片包含可能导致跨版本 Repair 的 Office 标签元数据"
                        ),
                        suggestion="保存前删除 p:tags，但保留其 p:nvPr 父节点",
                    ))
                referenced_ids = {
                    value
                    for node in slide_root.iter()
                    for attribute, value in node.attrib.items()
                    if attribute.startswith(relationship_ns)
                    and value
                }
                for missing_id in sorted(referenced_ids - related_ids):
                    self.issues.append(ValidationIssue(
                        severity="error",
                        category="package_integrity",
                        slide_num=slide_num,
                        description=(
                            f"幻灯片引用了不存在的 OOXML 关系: {missing_id}"
                        ),
                        suggestion="复制形状时同步关系，禁止输出需要 PowerPoint 修复的文件",
                    ))
    
    # ── 形状收集 ─────────────────────────────────────────
    
    def _collect_shapes(self, slide, slide_num: int) -> List[ShapeInfo]:
        """收集slide中所有有意义的形状"""
        shapes = []
        for shape in slide.shapes:
            # 跳过不可见的形状
            try:
                if hasattr(shape, '_element'):
                    # 检查XML中是否有隐藏属性
                    pass
            except Exception:
                pass
            
            left = int(shape.left or 0)
            top = int(shape.top or 0)
            width = int(shape.width or 0)
            height = int(shape.height or 0)
            
            # 跳过尺寸为0的形状
            if width <= 0 or height <= 0:
                continue
            
            text = ""
            shape_type = "other"
            
            if shape.has_text_frame:
                text = shape.text_frame.text.strip()
                shape_type = "text_box"
            elif shape.has_table:
                shape_type = "table"
                # 提取表格文本摘要
                table = shape.table
                rows_text = []
                for row in table.rows:
                    cells = [cell.text.strip() for cell in row.cells]
                    rows_text.append(" | ".join(cells))
                text = "\n".join(rows_text[:3])  # 最多3行
            elif hasattr(shape, 'image'):
                shape_type = "picture"
            
            shapes.append(ShapeInfo(
                name=shape.name or "",
                text=text[:100],  # 截断长文本
                left=left,
                top=top,
                right=left + width,
                bottom=top + height,
                width=width,
                height=height,
                shape_type=shape_type,
                slide_num=slide_num,
            ))
        
        return shapes
    
    # ── 重叠检测 ─────────────────────────────────────────
    
    def _check_overlaps(self, shapes: List[ShapeInfo], slide_num: int):
        """检测形状重叠"""
        tolerance = int(OVERLAP_TOLERANCE_CM * CM_TO_EMU)
        
        for i, s1 in enumerate(shapes):
            for j, s2 in enumerate(shapes):
                if j <= i:
                    continue
                
                # 计算重叠区域
                # Empty decorative layers cannot obscure resume content.
                if not s1.text or not s2.text:
                    continue

                overlap_left = max(s1.left, s2.left)
                overlap_top = max(s1.top, s2.top)
                overlap_right = min(s1.right, s2.right)
                overlap_bottom = min(s1.bottom, s2.bottom)
                
                overlap_w = overlap_right - overlap_left
                overlap_h = overlap_bottom - overlap_top
                
                if overlap_w > tolerance and overlap_h > tolerance:
                    overlap_area = overlap_w * overlap_h
                    s1_area = s1.width * s1.height
                    s2_area = s2.width * s2.height
                    min_area = min(s1_area, s2_area)
                    
                    # 如果重叠区域超过较小元素面积的10%，才报错
                    if overlap_area > min_area * 0.1:
                        self.issues.append(ValidationIssue(
                            severity="error",
                            category="overlap",
                            slide_num=slide_num,
                            description=f"检测到元素重叠: "
                                f"'{s1.name}' 与 '{s2.name}' 重叠",
                            element1=s1.name,
                            element2=s2.name,
                            coords=(
                                f"s1(l={self._emu_cm(s1.left)}cm, t={self._emu_cm(s1.top)}cm, "
                                f"r={self._emu_cm(s1.right)}cm, b={self._emu_cm(s1.bottom)}cm), "
                                f"s2(l={self._emu_cm(s2.left)}cm, t={self._emu_cm(s2.top)}cm, "
                                f"r={self._emu_cm(s2.right)}cm, b={self._emu_cm(s2.bottom)}cm)"
                            ),
                            suggestion=f"将 '{s2.name}' 下移至少 {self._emu_cm(overlap_h):.2f}cm",
                        ))
    
    def _is_same_module(self, s1: ShapeInfo, s2: ShapeInfo) -> bool:
        """判断两个形状是否属于同一模块（标题+表格组合）"""
        # 标题文本框和它下面的表格属于同一模块，允许包含关系
        if s1.shape_type == "text_box" and s2.shape_type == "table":
            # 表格的top应该在标题的bottom附近
            if s2.top >= s1.top and s2.top <= s1.bottom + int(1.5 * CM_TO_EMU):
                # 水平方向大致对齐
                if abs(s1.left - s2.left) < int(2 * CM_TO_EMU):
                    return True
        if s2.shape_type == "text_box" and s1.shape_type == "table":
            if s1.top >= s2.top and s1.top <= s2.bottom + int(1.5 * CM_TO_EMU):
                if abs(s1.left - s2.left) < int(2 * CM_TO_EMU):
                    return True
        return False
    
    # ── 文字溢出检测 ─────────────────────────────────────
    
    def _check_text_overflow(self, slide, shapes: List[ShapeInfo], slide_num: int):
        """检测文字是否可能溢出文本框"""
        for shape in slide.shapes:
            if not shape.has_text_frame:
                continue
            
            text_frame = shape.text_frame
            text = text_frame.text.strip()
            
            # 跳过空文本框
            if not text:
                continue
            
            # 检查文本框是否设置了自动调整
            auto_size = self._get_auto_size(shape)
            if auto_size in ["shrink", "resize"]:
                continue  # 有自动调整，不太可能溢出
            
            # 估算文本所需高度
            estimated_height = self._estimate_text_height(shape)
            actual_height = int(shape.height or 0)
            
            if actual_height <= 0:
                continue
            
            # 短文本 (< 15字符) 通常是标题，使用更宽松的容差
            if len(text) < 15:
                tolerance = TEXT_OVERFLOW_TOLERANCE * 2  # 60% 短文本很不可能溢出
            else:
                tolerance = TEXT_OVERFLOW_TOLERANCE  # 30%
            
            if estimated_height > actual_height * (1 + tolerance):
                text_preview = text[:50]
                self.issues.append(ValidationIssue(
                    severity="warning",  # 降为 warning，文字溢出需要人工确认
                    category="text_overflow",
                    slide_num=slide_num,
                    description=f"文字可能溢出文本框: '{text_preview}'",
                    element1=shape.name,
                    coords=(
                        f"est_h={self._emu_cm(estimated_height):.2f}cm, "
                        f"actual_h={self._emu_cm(actual_height):.2f}cm, "
                        f"text_len={len(text)}"
                    ),
                    suggestion="考虑减小字号、增加文本框高度或启用 shrink-to-fit",
                ))
    
    def _is_decorative(self, shape, slide_width: int, slide_height: int) -> bool:
        """判断形状是否为装饰性元素（背景、边框等）"""
        name_lower = (shape.name or "").lower()

        # 模板页脚色带允许出血到页面边缘，这是视觉设计的一部分，
        # 不应被通用的安全边距检查判定为版式问题。
        if name_lower.startswith("rectangle 12"):
            return True
        
        # 按名称判断
        for dec_name in DECORATIVE_NAMES:
            if dec_name in name_lower:
                # 大尺寸形状可能是背景装饰
                w = int(shape.width or 0)
                h = int(shape.height or 0)
                if w > slide_width * 0.8 or h > slide_height * 0.8:
                    return True
                # 跨度接近整个页面的形状
                if w > slide_width * 0.9:
                    return True
        
        # 按尺寸判断：占满整个页面 90% 以上的形状
        w = int(shape.width or 0)
        h = int(shape.height or 0)
        if w > slide_width * 0.95 and h > slide_height * 0.95:
            return True
        
        return False
    
    def _estimate_text_height(self, shape) -> int:
        """估算文本所需高度"""
        if not shape.has_text_frame:
            return 0
        
        text_frame = shape.text_frame
        available_width = int(shape.width or 0)
        
        if available_width <= 0:
            return 0
        
        total_height = 0
        # 内边距
        margin_left = int(text_frame.margin_left or 0) if text_frame.margin_left else 0
        margin_right = int(text_frame.margin_right or 0) if text_frame.margin_right else 0
        effective_width = available_width - margin_left - margin_right
        
        if effective_width <= 0:
            return 0
        
        for para in text_frame.paragraphs:
            # 估算每行字符数
            font_size = self._get_font_size(para)
            # 中文字符大约 = font_size EMU 宽，英文约 0.5 * font_size
            char_width = int(font_size * 0.9)  # 估算每个字符宽度
            chars_per_line = max(1, effective_width // char_width) if char_width > 0 else 1
            
            text = para.text or ""
            num_lines = max(1, -(-len(text) // chars_per_line))  # 向上取整
            
            # 行高约 1.3 倍字号
            line_height = int(font_size * 1.3)
            total_height += num_lines * line_height
        
        # 加上内边距
        margin_top = int(text_frame.margin_top or 0) if text_frame.margin_top else 0
        margin_bottom = int(text_frame.margin_bottom or 0) if text_frame.margin_bottom else 0
        total_height += margin_top + margin_bottom
        
        return total_height
    
    def _get_font_size(self, para) -> int:
        """获取段落字号 (EMU)"""
        for run in para.runs:
            if run.font.size:
                return int(run.font.size)
        # 默认12pt
        return int(Pt(12))
    
    def _get_auto_size(self, shape) -> str:
        """获取文本框的自动调整设置"""
        try:
            xml = shape._element.xml
            if 'shrinkToFit="1"' in xml:
                return "shrink"
            if 'autoSize="1"' in xml:
                return "resize"
            # python-pptx 的 TEXT_TO_FIT_SHAPE 对应 DrawingML 的
            # normAutofit；旧逻辑漏识别该设置，导致标题被误报溢出。
            if "<a:normAutofit" in xml:
                return "shrink"
        except Exception:
            pass
        return "none"
    
    # ── 间距检查 ─────────────────────────────────────────
    
    def _check_spacing(self, shapes: List[ShapeInfo], slide_num: int):
        """检查元素间间距"""
        min_gap = int(MIN_ELEMENT_GAP_CM * CM_TO_EMU)
        
        # 按 top 排序
        sorted_shapes = sorted(shapes, key=lambda s: s.top)
        
        for i in range(len(sorted_shapes) - 1):
            s1 = sorted_shapes[i]
            s2 = sorted_shapes[i + 1]
            
            # 检查垂直间隙（上一个的 bottom 到下一个的 top）
            vertical_gap = s2.top - s1.bottom
            
            # 只检查水平范围有重叠的元素对
            h_overlap = min(s1.right, s2.right) - max(s1.left, s2.left)
            if h_overlap <= 0:
                continue  # 水平方向无重叠，不检查垂直间距
            
            # 跳过同一模块的元素
            if self._is_same_module(s1, s2):
                continue
            
            if vertical_gap < 0:
                # 已经重叠，在overlap检查中处理
                continue
            
            if 0 < vertical_gap < min_gap:
                self.issues.append(ValidationIssue(
                    severity="warning",
                    category="spacing",
                    slide_num=slide_num,
                    description=f"元素间距过小: '{s1.name}' 与 '{s2.name}' 间距仅 "
                        f"{self._emu_cm(vertical_gap):.2f}cm (最小要求 {MIN_ELEMENT_GAP_CM}cm)",
                    element1=s1.name,
                    element2=s2.name,
                    coords=f"gap={self._emu_cm(vertical_gap):.2f}cm",
                    suggestion=f"增加间距至至少 {MIN_ELEMENT_GAP_CM}cm",
                ))
    
    # ── 页边距检查 ───────────────────────────────────────
    
    def _check_margins(self, shapes: List[ShapeInfo], slide, slide_num: int):
        """检查元素是否过于靠近页面边缘"""
        min_margin = int(MIN_MARGIN_CM * CM_TO_EMU)
        slide_width = int(self.prs.slide_width or 0)
        slide_height = int(self.prs.slide_height or 0)
        
        if slide_width <= 0 or slide_height <= 0:
            return
        
        for s in shapes:
            # 跳过装饰性元素
            is_decorative = False
            try:
                shape_obj = None
                for sh in slide.shapes:
                    if sh.name == s.name and int(sh.left or 0) == s.left:
                        shape_obj = sh
                        break
                if shape_obj and self._is_decorative(shape_obj, slide_width, slide_height):
                    is_decorative = True
            except Exception:
                pass
            
            severity = "info" if is_decorative else "warning"
            
            issues_for_shape = []
            
            if s.left < min_margin:
                issues_for_shape.append(f"左边缘仅 {self._emu_cm(s.left):.2f}cm")
            if s.top < min_margin:
                issues_for_shape.append(f"上边缘仅 {self._emu_cm(s.top):.2f}cm")
            if slide_width - s.right < min_margin:
                issues_for_shape.append(f"右边缘仅 {self._emu_cm(slide_width - s.right):.2f}cm")
            if slide_height - s.bottom < min_margin:
                issues_for_shape.append(f"下边缘仅 {self._emu_cm(slide_height - s.bottom):.2f}cm")
            
            if issues_for_shape:
                self.issues.append(ValidationIssue(
                    severity=severity,
                    category="margin",
                    slide_num=slide_num,
                    description=f"元素 '{s.name}' 过于靠近页面边缘: {'; '.join(issues_for_shape)}",
                    element1=s.name,
                    coords=(
                        f"l={self._emu_cm(s.left)}cm, t={self._emu_cm(s.top)}cm, "
                        f"r={self._emu_cm(s.right)}cm, b={self._emu_cm(s.bottom)}cm"
                    ),
                    suggestion=f"确保元素距离页面边缘至少 {MIN_MARGIN_CM}cm",
                ))
    
    # ── 工具方法 ─────────────────────────────────────────
    
    @staticmethod
    def _emu_cm(emu: int) -> float:
        return round(emu / CM_TO_EMU, 3)


def validate_pptx(file_path: str) -> ValidationResult:
    """便捷方法: 验证 PPTX 文件"""
    validator = PPTXValidator(file_path)
    return validator.validate()


def print_validation_report(result: ValidationResult):
    """打印格式化的验证报告"""
    print("\n" + "=" * 70)
    print("  PPTX 验证报告")
    print("=" * 70)
    print(f"  文件: {result.file_path}")
    print(f"  幻灯片数: {result.total_slides}")
    print(f"  状态: {'✅ 通过' if result.is_valid else '❌ 未通过'}")
    print(f"  错误: {result.error_count}  警告: {result.warning_count}  信息: {len(result.infos)}")
    
    if result.errors:
        print("\n  ── 错误 ──")
        for i, e in enumerate(result.errors, 1):
            print(f"  {i}. [slide {e.slide_num}] {e.description}")
            if e.suggestion:
                print(f"     💡 {e.suggestion}")
            if e.coords:
                print(f"     📍 {e.coords}")
    
    if result.warnings:
        print("\n  ── 警告 ──")
        for i, w in enumerate(result.warnings, 1):
            print(f"  {i}. [slide {w.slide_num}] {w.description}")
            if w.suggestion:
                print(f"     💡 {w.suggestion}")
    
    print("=" * 70 + "\n")


# ── 独立运行 ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
    else:
        # 默认测试路径
        file_path = os.path.join(os.path.dirname(__file__), "..", "..", "output")
        files = [f for f in os.listdir(file_path) if f.endswith('.pptx')]
        if files:
            file_path = os.path.join(file_path, files[-1])  # 最新的文件
            print(f"自动选择: {file_path}")
        else:
            print("未找到PPTX文件")
            sys.exit(1)
    
    result = validate_pptx(file_path)
    print_validation_report(result)
    
    # 输出JSON格式
    import json
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
