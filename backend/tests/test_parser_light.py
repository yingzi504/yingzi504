#!/usr/bin/env python3
"""
测试轻量级文档解析器
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.services.parser_service import (
    _check_unstructured,
    _check_pymupdf,
    _check_python_docx,
    _check_paddleocr
)


def test_parser_availability():
    """测试解析器可用性"""
    print("=" * 60)
    print("  测试解析器可用性")
    print("=" * 60)
    print()
    
    print("[1] 解析器检查:")
    
    unstructured_ok = _check_unstructured()
    pymupdf_ok = _check_pymupdf()
    python_docx_ok = _check_python_docx()
    paddleocr_ok = _check_paddleocr()
    
    print(f"  unstructured: {'✓ 可用' if unstructured_ok else '✗ 不可用'}")
    print(f"  pymupdf:      {'✓ 可用' if pymupdf_ok else '✗ 不可用'}")
    print(f"  python-docx:  {'✓ 可用' if python_docx_ok else '✗ 不可用'}")
    print(f"  paddleocr:    {'✓ 可用' if paddleocr_ok else '✗ 不可用'}")
    print()
    
    print("[2] 建议:")
    if pymupdf_ok and python_docx_ok:
        print("  ✓ 轻量级解析器已就绪，可以处理 PDF 和 Word")
    else:
        if not pymupdf_ok:
            print("  ! 建议安装: pip install pymupdf")
        if not python_docx_ok:
            print("  ! 建议安装: pip install python-docx")
    print()
    
    print("[3] 当前 requirements.txt 使用轻量级方案，")
    print("    不会下载 torch 或 paddlepaddle")
    print()
    
    print("=" * 60)


if __name__ == "__main__":
    test_parser_availability()
