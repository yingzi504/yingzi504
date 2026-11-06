"""
快捷测试脚本 — 直接发送 ResumeData JSON 到 /api/v1/resume/fill 端点

无需上传文件，直接使用预制的测试数据生成 PPT 简历。

用法:
    python tools/quick_test.py                                    # 使用中文测试数据
    python tools/quick_test.py --data en                          # 使用英文测试数据
    python tools/quick_test.py --file path/to/my_data.json        # 使用自定义数据
    python tools/quick_test.py --server http://localhost:8000     # 指定服务器地址
    python tools/quick_test.py --open                            # 测试完成后自动打开输出目录
    python tools/quick_test.py --help                             # 查看帮助

前置条件:
    - 后端服务已在运行 (默认 http://localhost:8000)
    - 测试数据文件存在于 backend/tests/test_data.json
"""

import argparse
import json
import os
import sys
import subprocess
import webbrowser
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.parse import urljoin

# ── 路径配置 ──
BASE_DIR = Path(__file__).resolve().parent.parent
TEST_DATA_DIR = BASE_DIR / "tests"
DEFAULT_SERVER = "http://localhost:8000"
API_PATH = "/api/v1/resume/fill"


def load_test_data(data_key: str) -> dict:
    """加载测试数据"""
    if data_key == "en":
        file_path = TEST_DATA_DIR / "test_data_en.json"
    else:
        file_path = TEST_DATA_DIR / "test_data.json"

    if not file_path.exists():
        print(f"❌ 测试数据文件不存在: {file_path}")
        sys.exit(1)

    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_custom_file(file_path: str) -> dict:
    """加载自定义 JSON 文件"""
    path = Path(file_path)
    if not path.exists():
        print(f"❌ 文件不存在: {path}")
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def send_request(server: str, payload: dict) -> dict:
    """发送 POST 请求到填充端点"""
    url = urljoin(server, API_PATH)
    data = json.dumps(payload).encode("utf-8")

    req = Request(url, data=data, method="POST")
    req.add_header("Content-Type", "application/json")

    print(f"📤 发送请求到: {url}")
    print(f"📋 简历姓名: {payload['resume_data'].get('name', 'N/A')}")
    print(f"📋 目标职位: {payload['resume_data'].get('position', 'N/A')}")
    print(f"📋 模板类型: {payload.get('template_type', 'vertical')}")
    print()

    try:
        with urlopen(req, timeout=300) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            return result
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        print()
        print("可能的原因:")
        print("  1. 后端服务未启动 — 请在终端运行后端服务器")
        print("  2. 地址错误 — 使用 --server 指定正确地址")
        print("  3. 网络问题 — 检查防火墙或代理设置")
        sys.exit(1)


def open_output_folder():
    """打开输出目录"""
    output_dir = BASE_DIR / "output"
    if output_dir.exists():
        if sys.platform == "win32":
            os.startdir(output_dir)
        elif sys.platform == "darwin":
            subprocess.run(["open", str(output_dir)])
        else:
            subprocess.run(["xdg-open", str(output_dir)])
        print(f"📂 已打开输出目录: {output_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="快捷简历测试 — 直接使用 JSON 数据生成 PPT",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python tools/quick_test.py                        # 中文测试数据
  python tools/quick_test.py --data en              # 英文测试数据
  python tools/quick_test.py --file my_resume.json  # 自定义数据
  python tools/quick_test.py --open                 # 自动打开输出目录
  python tools/quick_test.py --data en --open       # 英文测试 + 打开目录
        """,
    )
    parser.add_argument(
        "--data", "-d",
        choices=["zh", "en"],
        default="zh",
        help="使用内置测试数据: zh=中文, en=英文 (默认: zh)"
    )
    parser.add_argument(
        "--file", "-f",
        help="使用自定义 JSON 文件 (优先级高于 --data)"
    )
    parser.add_argument(
        "--server", "-s",
        default=DEFAULT_SERVER,
        help=f"后端服务地址 (默认: {DEFAULT_SERVER})"
    )
    parser.add_argument(
        "--open", "-o",
        action="store_true",
        help="完成后自动打开输出目录"
    )

    args = parser.parse_args()

    # ── 1. 加载数据 ──
    print("=" * 50)
    print("  🚀 AI 简历快捷测试工具")
    print("=" * 50)
    print()

    if args.file:
        print(f"📂 加载自定义文件: {args.file}")
        payload = load_custom_file(args.file)
    else:
        data_key = args.data
        print(f"📂 加载内置测试数据: {'英文' if data_key == 'en' else '中文'}")
        payload = load_test_data(data_key)

    # ── 2. 发送请求 ──
    result = send_request(args.server, payload)

    # ── 3. 显示结果 ──
    success = result.get("success", False)
    if success:
        filename = result.get("filename", "未知")
        pptx_url = result.get("pptx_download_url", "")
        file_size = result.get("file_size", 0)
        pdf_available = result.get("pdf_available", False)
        validation = result.get("validation", {})
        is_valid = validation.get("is_valid", True) if validation else True

        print(f"✅ PPT 生成成功!")
        print(f"📄 文件名: {filename}")
        print(f"📏 文件大小: {file_size / 1024:.1f} KB" if file_size else "")
        print(f"📎 下载 URL: {pptx_url}")
        if pdf_available:
            print(f"📎 PDF 下载 URL: {result.get('pdf_download_url', '')}")
        if not is_valid:
            error_count = validation.get("error_count", 0)
            print(f"⚠️  验证发现 {error_count} 个问题")
        print()
        print(f"💡 也可以通过浏览器访问 Swagger UI 进行测试:")
        print(f"   {urljoin(args.server, '/docs')}")
    else:
        msg = result.get("message", "未知错误")
        print(f"❌ PPT 生成失败: {msg}")

    # ── 4. 打开输出目录 ──
    if args.open and success:
        open_output_folder()

    print()
    print("=" * 50)


if __name__ == "__main__":
    main()
