"""
PPTX → PDF 转换服务
使用 LibreOffice headless 模式进行转换 (跨平台, 保真度高)
"""
import os
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional


class PdfConverterService:
    """PPTX → PDF 转换"""

    # LibreOffice 常见安装路径 (Windows)
    _LIBREOFFICE_PATHS = [
        r"C:\Program Files\LibreOffice\program\soffice.exe",
        r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        r"C:\LibreOffice\program\soffice.exe",
    ]

    @staticmethod
    def find_libreoffice() -> Optional[str]:
        """自动查找 LibreOffice 可执行文件"""
        # 1. 检查环境变量
        env_path = shutil.which("soffice")
        if env_path:
            return env_path

        # 2. 检查常见安装路径
        for path in PdfConverterService._LIBREOFFICE_PATHS:
            if os.path.exists(path):
                return path

        return None

    @staticmethod
    def convert_pptx_to_pdf(pptx_path: str, output_dir: Optional[str] = None) -> str:
        """
        将 PPTX 文件转换为 PDF

        Args:
            pptx_path: PPTX 文件绝对路径
            output_dir: PDF 输出目录 (默认与 PPTX 同目录)

        Returns:
            生成的 PDF 文件路径

        Raises:
            FileNotFoundError: LibreOffice 未安装
            RuntimeError: 转换失败
        """
        if not os.path.exists(pptx_path):
            raise FileNotFoundError(f"PPTX 文件不存在: {pptx_path}")

        soffice = PdfConverterService.find_libreoffice()
        if not soffice:
            raise FileNotFoundError(
                "未找到 LibreOffice。请安装 LibreOffice 以支持 PDF 转换。\n"
                "下载地址: https://www.libreoffice.org/download/\n"
                "安装后确保 soffice.exe 在 PATH 中或在默认安装路径。"
            )

        # 确定输出目录
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(pptx_path))
        os.makedirs(output_dir, exist_ok=True)

        # 预期输出的 PDF 文件名
        base_name = os.path.splitext(os.path.basename(pptx_path))[0]
        expected_pdf = os.path.join(output_dir, f"{base_name}.pdf")
        # Use a short temporary basename so long anonymized/job-position names
        # do not prevent LibreOffice from producing the PDF.
        work_dir = tempfile.mkdtemp(prefix="iav_pdf_")
        short_pptx = os.path.join(work_dir, "resume.pptx")
        short_pdf = os.path.join(work_dir, "resume.pdf")
        profile_dir = os.path.join(work_dir, "lo_profile")
        shutil.copy2(pptx_path, short_pptx)

        print(f"🔄 正在转换 PPTX → PDF: {os.path.basename(pptx_path)}")
        print(f"   LibreOffice: {soffice}")

        try:
            result = subprocess.run(
                [
                    soffice,
                    f"-env:UserInstallation={Path(profile_dir).as_uri()}",
                    "--headless",
                    "--convert-to", "pdf",
                    "--outdir", work_dir,
                    short_pptx,
                ],
                capture_output=True,
                text=True,
                timeout=120,  # 2 分钟超时
                env={**os.environ, "HOME": os.path.expanduser("~")},
            )

            if result.returncode != 0:
                stderr = result.stderr.strip()
                raise RuntimeError(f"LibreOffice 转换失败 (code={result.returncode}): {stderr}")

            if not os.path.exists(short_pdf):
                raise RuntimeError(f"PDF 文件未生成: {expected_pdf}")

            shutil.copy2(short_pdf, expected_pdf)

            pdf_size = os.path.getsize(expected_pdf)
            print(f"   ✅ PDF 生成成功: {os.path.basename(expected_pdf)} ({pdf_size} bytes)")
            return expected_pdf

        except subprocess.TimeoutExpired:
            raise RuntimeError("PPTX → PDF 转换超时 (超过120秒)")
        except FileNotFoundError:
            raise FileNotFoundError(f"LibreOffice 可执行文件无效: {soffice}")
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

    @staticmethod
    def is_available() -> bool:
        """检查 PDF 转换是否可用"""
        return PdfConverterService.find_libreoffice() is not None

    @staticmethod
    def ensure_pdf_for_pptx(pptx_path: str, output_dir: Optional[str] = None) -> str:
        """Return an existing PDF or create it from the supplied PPTX."""
        target_dir = output_dir or os.path.dirname(os.path.abspath(pptx_path))
        expected = os.path.join(
            target_dir, f"{Path(pptx_path).stem}.pdf"
        )
        if os.path.isfile(expected) and os.path.getsize(expected) > 0:
            return expected
        return PdfConverterService.convert_pptx_to_pdf(pptx_path, target_dir)
