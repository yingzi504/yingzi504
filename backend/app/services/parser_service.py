"""
文件解析服务
支持PDF/Word/图片解析
使用 unstructured + PaddleOCR 实现 Pipeline 步骤 1
"""
import os
import time
import traceback
from zipfile import BadZipFile, ZipFile
from xml.etree import ElementTree as ET
from typing import Optional, Tuple
from pathlib import Path
from fastapi import HTTPException

# 可选依赖 - 懒加载
_unstructured_available = None
_pymupdf_available = None
_python_docx_available = None
_paddleocr_available = None
_paddleocr_instance = None


def _check_unstructured():
    """检查unstructured是否可用"""
    global _unstructured_available
    if _unstructured_available is None:
        try:
            from unstructured.partition.pdf import partition_pdf
            from unstructured.partition.docx import partition_docx
            from unstructured.partition.image import partition_image
            _unstructured_available = True
        except Exception:
            print(f"[parser_service] unstructured 不可用:")
            traceback.print_exc()
            _unstructured_available = False
    return _unstructured_available


def _check_pymupdf():
    """检查pymupdf是否可用"""
    global _pymupdf_available
    if _pymupdf_available is None:
        try:
            import fitz  # pymupdf
            _pymupdf_available = True
        except Exception:
            print(f"[parser_service] pymupdf 不可用:")
            traceback.print_exc()
            _pymupdf_available = False
    return _pymupdf_available


def _check_python_docx():
    """检查python-docx是否可用"""
    global _python_docx_available
    if _python_docx_available is None:
        try:
            from docx import Document
            _python_docx_available = True
        except Exception:
            print(f"[parser_service] python-docx 不可用:")
            traceback.print_exc()
            _python_docx_available = False
    return _python_docx_available


def _check_paddleocr():
    """检查paddleocr是否可用"""
    global _paddleocr_available
    if _paddleocr_available is None:
        try:
            from paddleocr import PaddleOCR
            _paddleocr_available = True
        except Exception:
            print(f"[parser_service] paddleocr 不可用:")
            traceback.print_exc()
            _paddleocr_available = False
    return _paddleocr_available


def _get_paddleocr():
    """获取PaddleOCR实例"""
    global _paddleocr_instance
    if _paddleocr_instance is None:
        from paddleocr import PaddleOCR
        _paddleocr_instance = PaddleOCR(use_angle_cls=True, lang="ch", show_log=False)
    return _paddleocr_instance


class ParserService:
    """文件解析服务"""

    _WORD_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"

    @staticmethod
    def _parse_docx_ooxml_text(file_path: str) -> str:
        """Extract body and header text directly from DOCX OOXML."""
        try:
            with ZipFile(file_path) as archive:
                part_names = sorted(
                    name
                    for name in archive.namelist()
                    if name.startswith("word/header") and name.endswith(".xml")
                )
                part_names.append("word/document.xml")
                xml_parts = [archive.read(name) for name in part_names]
        except (BadZipFile, KeyError, ET.ParseError, OSError):
            return ""

        text_tag = f"{{{ParserService._WORD_NS}}}t"
        paragraph_tag = f"{{{ParserService._WORD_NS}}}p"
        lines = []
        try:
            for xml_part in xml_parts:
                root = ET.fromstring(xml_part)
                for paragraph in root.iter(paragraph_tag):
                    value = "".join(node.text or "" for node in paragraph.iter(text_tag))
                    if value.strip():
                        lines.append(value)
        except ET.ParseError:
            return ""
        return "\n".join(lines)

    @staticmethod
    def _merge_docx_ooxml_text(parsed_text: str, ooxml_text: str) -> str:
        """Use OOXML as the stable DOCX text source when it is available."""
        parsed_text = (parsed_text or "").strip()
        ooxml_text = (ooxml_text or "").strip()
        return ooxml_text or parsed_text
    
    # 支持的文件扩展名
    SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".jpg", ".jpeg", ".png", ".bmp", ".tiff"}
    
    @staticmethod
    def _get_file_type(file_path: str) -> str:
        """
        获取文件类型
        
        Args:
            file_path: 文件路径
            
        Returns:
            文件类型标识（pdf/docx/image）
        """
        ext = Path(file_path).suffix.lower()
        if ext == ".pdf":
            return "pdf"
        elif ext in {".docx", ".doc"}:
            return "docx"
        elif ext in {".jpg", ".jpeg", ".png", ".bmp", ".tiff"}:
            return "image"
        else:
            raise HTTPException(status_code=400, detail=f"不支持的文件类型: {ext}")
    
    @staticmethod
    async def _parse_with_unstructured(file_path: str, file_type: str) -> Tuple[str, Optional[int]]:
        """
        使用 unstructured 库解析文档
        
        Args:
            file_path: 文件路径
            file_type: 文件类型
            
        Returns:
            (解析文本, 页数)
        """
        if not _check_unstructured():
            # 尝试使用轻量级备选方案
            if file_type == "pdf" and _check_pymupdf():
                return await ParserService._parse_with_pymupdf(file_path)
            elif file_type == "docx" and _check_python_docx():
                return await ParserService._parse_with_python_docx(file_path)
            else:
                raise HTTPException(
                    status_code=501,
                    detail="unstructured 库未安装，请安装: pip install 'unstructured[pdf,docx]' 或 pymupdf/python-docx"
                )
        
        # 延迟导入
        from unstructured.partition.pdf import partition_pdf
        from unstructured.partition.docx import partition_docx
        from unstructured.partition.image import partition_image
        
        try:
            if file_type == "pdf":
                elements = partition_pdf(filename=file_path)
                page_count = len({e.metadata.page_number for e in elements if e.metadata.page_number})
            elif file_type == "docx":
                elements = partition_docx(filename=file_path)
                page_count = None
            else:  # image
                elements = partition_image(filename=file_path)
                page_count = 1
            
            text_content = "\n".join([str(el) for el in elements])
            return text_content, page_count
            
        except Exception as e:
            raise HTTPException(
                status_code=422, 
                detail=f"unstructured 解析失败: {str(e)}"
            )
    
    @staticmethod
    async def _parse_with_pymupdf(file_path: str) -> Tuple[str, int]:
        """
        使用 pymupdf (PyMuPDF) 轻量解析 PDF
        
        Args:
            file_path: PDF 文件路径
            
        Returns:
            (解析文本, 页数)
        """
        if not _check_pymupdf():
            raise HTTPException(
                status_code=501,
                detail="pymupdf 库未安装，请先安装: pip install pymupdf"
            )
        
        try:
            import fitz
            
            doc = fitz.open(file_path)
            page_count = len(doc)
            text_lines = []
            
            for page in doc:
                text = page.get_text()
                text_lines.append(text)
            
            doc.close()
            text_content = "\n".join(text_lines)
            return text_content, page_count
            
        except Exception as e:
            raise HTTPException(
                status_code=422, 
                detail=f"pymupdf 解析失败: {str(e)}"
            )
    
    @staticmethod
    async def _parse_with_python_docx(file_path: str) -> Tuple[str, Optional[int]]:
        """
        使用 python-docx 轻量解析 Word 文档
        
        Args:
            file_path: DOCX 文件路径
            
        Returns:
            (解析文本, None)
        """
        if not _check_python_docx():
            raise HTTPException(
                status_code=501,
                detail="python-docx 库未安装，请先安装: pip install python-docx"
            )
        
        try:
            from docx import Document
            
            doc = Document(file_path)
            text_lines = []
            
            # 提取段落文本
            for para in doc.paragraphs:
                if para.text.strip():
                    text_lines.append(para.text)
            
            # 提取表格文本
            for table in doc.tables:
                for row in table.rows:
                    row_text = " | ".join([cell.text.strip() for cell in row.cells if cell.text.strip()])
                    if row_text:
                        text_lines.append(row_text)
            
            return "\n".join(text_lines), None
            
        except Exception as e:
            raise HTTPException(
                status_code=422, 
                detail=f"python-docx 解析失败: {str(e)}"
            )
    
    @staticmethod
    async def _parse_with_ocr(file_path: str) -> str:
        """
        使用 PaddleOCR 进行 OCR 识别
        
        Args:
            file_path: 文件路径
            
        Returns:
            OCR 识别的文本
        """
        if not _check_paddleocr():
            raise HTTPException(
                status_code=501,
                detail="paddleocr 库未安装，请先安装: pip install paddleocr paddlepaddle"
            )
        
        try:
            ocr = _get_paddleocr()
            result = ocr.ocr(file_path, cls=True)
            
            # 提取文本
            text_lines = []
            if result and result[0]:
                for line in result[0]:
                    if line and len(line) >= 2 and line[1]:
                        text_lines.append(line[1][0])
            
            return "\n".join(text_lines)
            
        except Exception as e:
            raise HTTPException(
                status_code=422, 
                detail=f"OCR 识别失败: {str(e)}"
            )
    
    @staticmethod
    async def parse_file(file_path: str, original_filename: str) -> dict:
        """
        解析简历文件（Pipeline 步骤 1）
        
        Args:
            file_path: 文件路径
            original_filename: 原始文件名
            
        Returns:
            解析结果字典
        """
        start_time = time.time()
        
        try:
            # 验证文件是否存在
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="文件不存在")
            
            # 获取文件类型
            file_type = ParserService._get_file_type(file_path)
            
            text_content = ""
            page_count = None
            parse_method = ""
            
            # 根据文件类型选择解析方式
            if file_type in {"pdf", "docx"}:
                # 按优先级尝试解析器
                parse_method = ""
                
                # 1. 尝试 unstructured
                if _check_unstructured():
                    try:
                        text_content, page_count = await ParserService._parse_with_unstructured(file_path, file_type)
                        parse_method = "unstructured"
                    except Exception:
                        pass
                
                # 2. 如果 unstructured 失败或不可用，尝试轻量级解析器
                if not parse_method:
                    if file_type == "pdf" and _check_pymupdf():
                        text_content, page_count = await ParserService._parse_with_pymupdf(file_path)
                        parse_method = "pymupdf"
                    elif file_type == "docx" and _check_python_docx():
                        text_content, page_count = await ParserService._parse_with_python_docx(file_path)
                        parse_method = "python-docx"
                
                # 3. 如果都失败且是 PDF，尝试 OCR
                if not parse_method and file_type == "pdf" and _check_paddleocr():
                    text_content = await ParserService._parse_with_ocr(file_path)
                    parse_method = "ocr"
                
                # 4. 如果还没有解析成功，抛出错误
                if not parse_method:
                    available = []
                    if _check_unstructured():
                        available.append("unstructured")
                    if file_type == "pdf" and _check_pymupdf():
                        available.append("pymupdf")
                    if file_type == "docx" and _check_python_docx():
                        available.append("python-docx")
                    if _check_paddleocr():
                        available.append("paddleocr")
                    
                    raise HTTPException(
                        status_code=501,
                        detail=f"没有可用的解析器。请安装至少一个: unstructured, pymupdf, python-docx。当前可用: {available}"
                    )
                
                # 如果提取文本为空且是 PDF，尝试 OCR
                # Both unstructured and python-docx can omit drawing text and
                # header fields such as the candidate name.
                if file_type == "docx":
                    text_content = ParserService._merge_docx_ooxml_text(
                        text_content,
                        ParserService._parse_docx_ooxml_text(file_path),
                    )

                if not text_content.strip() and file_type == "pdf" and _check_paddleocr():
                    text_content = await ParserService._parse_with_ocr(file_path)
                    parse_method = "ocr"
            else:  # image
                text_content = await ParserService._parse_with_ocr(file_path)
                parse_method = "ocr"
            
            # 验证解析结果
            if not text_content.strip():
                raise HTTPException(status_code=422, detail="无法从文件中提取文本内容")
            
            parse_duration = time.time() - start_time
            
            return {
                "file_id": Path(file_path).stem,
                "original_file": original_filename,
                "text_content": text_content,
                "file_type": file_type,
                "parse_method": parse_method,
                "parse_duration": parse_duration,
                "page_count": page_count
            }
            
        except HTTPException:
            raise
        except Exception as e:
            # 标准化错误响应
            error_detail = f"文件解析失败: {str(e)}"
            print(f"[Parser Error] {error_detail}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_detail)

