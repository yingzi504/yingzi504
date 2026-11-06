# -*- coding: utf-8 -*-
"""
验证无分号 tasks 的启发式切分与多行格式化
使用用户报告的真实样例（不调用 LLM）
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.services.summarization_service import SummarizationService

# 用户报告的第二段项目经历（无分号，空格连接）
TASKS_NO_SEMICOLON = (
    "协助完成项目计划 完成车型筛选 确认各阶段试验完成节点 完成OBD系族分类 "
    "确认车辆强检认证批次 接收试制阶段车型 升级车辆ECU和TCU数据 执行特定功能测试 "
    "排查动力总成相关故障码 保障车辆与INCA软件正常通讯 开展后续验证试验 "
    "确定整车油耗水平 完成十六万公里耐久 常温排放 OBD 蒸发排放等整车排放相关试验 "
    "支持完成相关车型的强检认证试验 完成试验报告总结 推进新型催化器量产适用"
)

# 第一段项目经历（有分号，参考正确格式）
TASKS_WITH_SEMICOLON = (
    "制定新车型动力总成相关、整备/测试质量、车型、油耗目标及百公里加速、等速油耗、"
    "爬坡度等性能参数；制定评价验证试验计划，考虑评价试验项目、试验时间、车辆磨合时间、"
    "功能性故障\n用INCA及MDA软件验证标定不同版本EMS数据，完成车辆油耗及各项排放试验；"
    "提供强检认证试验期间突发的AMS、ISG功能故障或发动机无法启动等问题的技术支援"
)

# 含"协助完成"、"完成节点"、"支持完成"等易误切陷阱的样例
TASKS_TRAP = (
    "协助完成项目计划 完成车型筛选 确认各阶段试验完成节点 完成OBD系族分类 "
    "支持完成相关车型的强检认证试验"
)

# 英文无分号样例
TASKS_EN = (
    "Managed project timeline Budget planning "
    "Coordinated with cross-functional teams Executed functional tests "
    "Resolved powertrain fault codes"
)


def main():
    print("=" * 70)
    print("测试 1: _split_text_into_bullets（无分号中文样例）")
    print("=" * 70)
    bullets = SummarizationService._split_text_into_bullets(TASKS_NO_SEMICOLON)
    print(f"切分点数: {len(bullets)}")
    for i, b in enumerate(bullets, 1):
        print(f"  [{i}] {b}")

    print()
    print("=" * 70)
    print("测试 2: _split_text_into_bullets（易误切陷阱样例）")
    print("=" * 70)
    bullets = SummarizationService._split_text_into_bullets(TASKS_TRAP)
    print(f"切分点数: {len(bullets)}")
    for i, b in enumerate(bullets, 1):
        print(f"  [{i}] {b}")

    print()
    print("=" * 70)
    print("测试 3: _split_text_into_bullets（英文样例）")
    print("=" * 70)
    bullets = SummarizationService._split_text_into_bullets(TASKS_EN)
    print(f"切分点数: {len(bullets)}")
    for i, b in enumerate(bullets, 1):
        print(f"  [{i}] {b}")

    print()
    print("=" * 70)
    print("测试 4: _format_multiline_tasks（无分号中文 → 应多行）")
    print("=" * 70)
    formatted = SummarizationService._format_multiline_tasks(TASKS_NO_SEMICOLON, "CN")
    print(repr(formatted))
    print("--- 渲染效果 ---")
    print(formatted.replace('；\n', '；\n'))

    print()
    print("=" * 70)
    print("测试 5: _format_multiline_tasks（有分号中文 → 不变式多行）")
    print("=" * 70)
    formatted = SummarizationService._format_multiline_tasks(TASKS_WITH_SEMICOLON, "CN")
    print(repr(formatted))

    print()
    print("=" * 70)
    print("测试 6: _format_multiline_tasks（英文无分号 → 应多行）")
    print("=" * 70)
    formatted = SummarizationService._format_multiline_tasks(TASKS_EN, "EN")
    print(repr(formatted))
    print("--- 渲染效果 ---")
    print(formatted.replace(';\n', ';\n'))

    # 断言：无分号中文样例应切分出多个要点
    bullets = SummarizationService._split_text_into_bullets(TASKS_NO_SEMICOLON)
    assert len(bullets) > 5, f"期望切分>5个要点，实际 {len(bullets)}"
    formatted = SummarizationService._format_multiline_tasks(TASKS_NO_SEMICOLON, "CN")
    assert '\n' in formatted, "无分号样例应输出多行"
    print()
    print("✅ 所有断言通过")


if __name__ == "__main__":
    main()
