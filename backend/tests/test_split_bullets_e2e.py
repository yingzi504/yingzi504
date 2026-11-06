# -*- coding: utf-8 -*-
"""
端到端验证：无分号 tasks 的摘要优化（真实调用 LLM）
验证第二段项目经历（无分号）与第一段（有分号）输出格式一致
"""
import sys
import os

# ── Windows SSL 修复（必须在导入任何第三方库前）──
import ssl
import certifi
_original_load_windows = ssl.SSLContext._load_windows_store_certs
def _patched_load_windows(self, storename, purpose):
    pass
ssl.SSLContext._load_windows_store_certs = _patched_load_windows
_cafile = certifi.where()
os.environ["SSL_CERT_FILE"] = _cafile
os.environ["REQUESTS_CA_BUNDLE"] = _cafile
os.environ["CURL_CA_BUNDLE"] = _cafile

_BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(_BASE_DIR)
sys.path.insert(0, _BASE_DIR)

from app.services.summarization_service import SummarizationService

# 第二段项目经历（用户报告：无分号，空格连接）
TASKS_NO_SEMICOLON = (
    "协助完成项目计划 完成车型筛选 确认各阶段试验完成节点 完成OBD系族分类 "
    "确认车辆强检认证批次 接收试制阶段车型 升级车辆ECU和TCU数据 执行特定功能测试 "
    "排查动力总成相关故障码 保障车辆与INCA软件正常通讯 开展后续验证试验 "
    "确定整车油耗水平 完成十六万公里耐久 常温排放 OBD 蒸发排放等整车排放相关试验 "
    "支持完成相关车型的强检认证试验 完成试验报告总结 推进新型催化器量产适用"
)

# 第一段项目经历（有分号，参考格式）
TASKS_WITH_SEMICOLON = (
    "制定新车型动力总成相关、整备/测试质量、车型、油耗目标及百公里加速、等速油耗、"
    "爬坡度等性能参数；制定评价验证试验计划，考虑评价试验项目、试验时间、车辆磨合时间、"
    "功能性故障；用INCA及MDA软件验证标定不同版本EMS数据，完成车辆油耗及各项排放试验；"
    "提供强检认证试验期间突发的AMS、ISG功能故障或发动机无法启动等问题的技术支援"
)

import asyncio


async def main():
    print("=" * 70)
    print("原始（第二段，无分号）:")
    print(TASKS_NO_SEMICOLON)
    print()
    print("=" * 70)
    print("优化后（第二段）:")
    optimized = await SummarizationService.summarize_text(TASKS_NO_SEMICOLON, "CN")
    formatted = SummarizationService._format_multiline_tasks(optimized, "CN")
    print(repr(formatted))
    print("--- 渲染效果 ---")
    print(formatted)

    print()
    print("=" * 70)
    print("优化后（第一段，对照）:")
    optimized1 = await SummarizationService.summarize_text(TASKS_WITH_SEMICOLON, "CN")
    formatted1 = SummarizationService._format_multiline_tasks(optimized1, "CN")
    print(repr(formatted1))
    print("--- 渲染效果 ---")
    print(formatted1)

    print()
    print("=" * 70)
    print("检查结果:")
    lines2 = [l for l in formatted.split('\n') if l.strip()]
    lines1 = [l for l in formatted1.split('\n') if l.strip()]
    print(f"  第二段行数: {len(lines2)}")
    print(f"  第一段行数: {len(lines1)}")
    if len(lines2) >= 3 and len(lines1) >= 3:
        print("  ✅ 两段均输出多行格式，格式已统一")
    else:
        print("  ⚠️ 格式检查未达预期")


if __name__ == "__main__":
    asyncio.run(main())
