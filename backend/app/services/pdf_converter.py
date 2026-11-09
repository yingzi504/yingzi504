"""PPTX → PDF conversion with LibreOffice and Windows PowerPoint fallback."""
import os
import logging
import subprocess
import shutil
import tempfile
from pathlib import Path
from typing import Optional


logger = logging.getLogger(__name__)


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
    def has_powerpoint() -> bool:
        """Return whether Microsoft PowerPoint COM is registered on Windows."""
        if os.name != "nt":
            return False
        try:
            import winreg
            with winreg.OpenKey(
                winreg.HKEY_CLASSES_ROOT, r"PowerPoint.Application\CLSID"
            ):
                return True
        except OSError:
            return False

    @staticmethod
    def _convert_with_powerpoint(pptx_path: str, expected_pdf: str) -> str:
        """Export through PowerPoint COM using the Windows PowerShell host."""
        work_dir = tempfile.mkdtemp(prefix="iav_ppt_pdf_")
        short_pptx = os.path.join(work_dir, "resume.pptx")
        short_pdf = os.path.join(work_dir, "resume.pdf")
        shutil.copy2(pptx_path, short_pptx)
        try:
            powershell = shutil.which("powershell.exe") or shutil.which("powershell")
            if not powershell:
                raise RuntimeError("未找到 Windows PowerShell")
            script = r"""
$source = $env:IAV_PPTX_SOURCE
$destination = $env:IAV_PDF_DESTINATION
$application = $null
$presentation = $null
try {
    $application = New-Object -ComObject PowerPoint.Application
    $presentation = $application.Presentations.Open($source, $true, $false, $false)
    # ppSaveAsPDF = 32. This is compatible with PowerPoint 2007.
    $presentation.SaveAs($destination, 32)
} finally {
    if ($presentation) {
        try { $presentation.Close() } catch {}
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($presentation)
    }
    if ($application) {
        try { $application.Quit() } catch {}
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($application)
    }
}
"""
            result = subprocess.run(
                [
                    powershell, "-NoProfile", "-NonInteractive",
                    "-ExecutionPolicy", "Bypass", "-Command", script,
                ],
                capture_output=True,
                text=True,
                timeout=120,
                env={
                    **os.environ,
                    "IAV_PPTX_SOURCE": os.path.abspath(short_pptx),
                    "IAV_PDF_DESTINATION": os.path.abspath(short_pdf),
                },
            )
            if result.returncode != 0:
                detail = (result.stderr or result.stdout).strip()
                raise RuntimeError(
                    f"PowerPoint 进程返回 code={result.returncode}: {detail}"
                )
            if not os.path.isfile(short_pdf) or os.path.getsize(short_pdf) <= 0:
                detail = (result.stderr or result.stdout).strip()
                raise RuntimeError(
                    f"PowerPoint 未生成有效的 PDF 文件: {detail or '无诊断输出'}"
                )
            shutil.copy2(short_pdf, expected_pdf)
            return expected_pdf
        except subprocess.TimeoutExpired as exc:
            raise RuntimeError("PowerPoint PDF 转换超时（超过120秒）") from exc
        except Exception as exc:
            raise RuntimeError(f"PowerPoint PDF 转换失败: {exc}") from exc
        finally:
            shutil.rmtree(work_dir, ignore_errors=True)

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
        if not soffice and not PdfConverterService.has_powerpoint():
            raise FileNotFoundError(
                "未找到可用的 PDF 转换器。请安装 LibreOffice，或在 Windows 上安装 Microsoft PowerPoint。"
            )

        # 确定输出目录
        if output_dir is None:
            output_dir = os.path.dirname(os.path.abspath(pptx_path))
        os.makedirs(output_dir, exist_ok=True)

        # 预期输出的 PDF 文件名
        base_name = os.path.splitext(os.path.basename(pptx_path))[0]
        expected_pdf = os.path.join(output_dir, f"{base_name}.pdf")
        if not soffice:
            logger.info(
                "Converting PPTX to PDF with Microsoft PowerPoint: %s",
                os.path.basename(pptx_path),
            )
            return PdfConverterService._convert_with_powerpoint(
                pptx_path, expected_pdf
            )

        # Use a short temporary basename so long anonymized/job-position names
        # do not prevent LibreOffice from producing the PDF.
        work_dir = tempfile.mkdtemp(prefix="iav_pdf_")
        short_pptx = os.path.join(work_dir, "resume.pptx")
        short_pdf = os.path.join(work_dir, "resume.pdf")
        profile_dir = os.path.join(work_dir, "lo_profile")
        shutil.copy2(pptx_path, short_pptx)

        logger.info(
            "Converting PPTX to PDF with LibreOffice: %s",
            os.path.basename(pptx_path),
        )

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
            logger.info(
                "PDF generated successfully: %s (%d bytes)",
                os.path.basename(expected_pdf), pdf_size,
            )
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
        return (
            PdfConverterService.find_libreoffice() is not None
            or PdfConverterService.has_powerpoint()
        )

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
