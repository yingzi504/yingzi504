"""
验证测试：步骤2.4 - 文档解析服务（Pipeline 步骤 1）
"""
import sys
import os
import time
from pathlib import Path

# 添加项目路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from fastapi import HTTPException
from app.services.parser_service import ParserService


async def test_parser_service():
    """测试解析服务"""
    print("=" * 60)
    print("验证测试：步骤2.4 - 文档解析服务")
    print("=" * 60)
    
    # 创建测试上传目录
    test_uploads = "test_uploads"
    os.makedirs(test_uploads, exist_ok=True)
    
    test_cases = [
        {
            "name": "1. 测试文件类型判断",
            "func": test_file_type_detection
        },
        {
            "name": "2. 测试错误处理（文件不存在）",
            "func": test_file_not_found
        },
        {
            "name": "3. 测试错误处理（不支持的格式）",
            "func": test_unsupported_format
        }
    ]
    
    passed = 0
    failed = 0
    
    for test in test_cases:
        print(f"\n{test['name']}")
        print("-" * 60)
        try:
            await test["func"]()
            print("✓ 测试通过")
            passed += 1
        except Exception as e:
            print(f"✗ 测试失败: {str(e)}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"测试结果: {passed} 通过, {failed} 失败")
    print("=" * 60)
    
    return failed == 0


async def test_file_type_detection():
    """测试文件类型判断"""
    test_files = {
        "test.pdf": "pdf",
        "test.docx": "docx",
        "test.doc": "docx",
        "test.jpg": "image",
        "test.png": "image",
    }
    
    for filename, expected_type in test_files.items():
        file_path = os.path.join("test_uploads", filename)
        # 创建空文件
        open(file_path, "a").close()
        detected_type = ParserService._get_file_type(file_path)
        assert detected_type == expected_type, f"{filename}: 期望 {expected_type}, 实际 {detected_type}"
        print(f"  ✓ {filename} -> {detected_type}")


async def test_file_not_found():
    """测试文件不存在错误"""
    try:
        await ParserService.parse_file("nonexistent_file.pdf", "nonexistent_file.pdf")
        assert False, "应该抛出 HTTPException"
    except HTTPException as e:
        assert e.status_code == 404
        print("  ✓ 正确抛出 404 错误")


async def test_unsupported_format():
    """测试不支持的格式"""
    test_file = os.path.join("test_uploads", "test.exe")
    open(test_file, "a").close()
    
    try:
        await ParserService.parse_file(test_file, "test.exe")
        assert False, "应该抛出 HTTPException"
    except HTTPException as e:
        assert e.status_code == 400
        print("  ✓ 正确抛出 400 错误")


if __name__ == "__main__":
    success = asyncio.run(test_parser_service())
    sys.exit(0 if success else 1)
