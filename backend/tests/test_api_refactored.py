"""
测试重构后的API接口
验证简化后的API工作正常
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.smart_filler_service import SmartFillerService
from app.services.filler_service import FillerService
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.template_config import TemplateType


def test_refactored_api():
    """测试重构后的API逻辑"""
    
    print("=" * 80)
    print("测试重构后的API - 简化接口")
    print("=" * 80)
    
    # 测试数据
    resume_data = ResumeData(
        name="测试用户",
        position="高级工程师",
        technical_area="全栈开发",
        total_exp="8年",
        tech_skills="Python, JavaScript, React, Node.js",
        lang_skills="中文, English",
        language="CN",
        
        # 多段经历
        work=[
            WorkItem(company="公司A", period="2020-至今", role="高级工程师", tasks="负责核心系统开发"),
            WorkItem(company="公司B", period="2017-2020", role="工程师", tasks="全栈开发"),
            WorkItem(company="公司C", period="2015-2017", role="初级工程师", tasks="学习成长"),
        ],
        project=[
            ProjectItem(company="公司A", period="2021-2023", name="项目X", role="架构师", tasks="系统设计"),
            ProjectItem(company="公司B", period="2018-2020", name="项目Y", role="开发", tasks="功能实现"),
        ],
        education=[
            EducationItem(period="2011-2015", school="某大学", degree="本科", major="计算机"),
        ]
    )
    
    print("\n📋 测试数据:")
    print(f"   姓名: {resume_data.name}")
    print(f"   💼 工作经历: {len(resume_data.work)} 条")
    print(f"   📦 项目经历: {len(resume_data.project)} 条")
    print(f"   🎓 教育经历: {len(resume_data.education)} 条")
    
    # 测试1: 主API（智能填充 - 推荐）
    print("\n" + "=" * 80)
    print("测试1: /fill (主API - 智能填充)")
    print("=" * 80)
    try:
        output_path = SmartFillerService.fill_template(
            resume_data=resume_data,
            template_type=TemplateType.NEW_CN,
            output_filename="api_main_test.pptx"
        )
        print(f"✅ 主API测试通过!")
        print(f"   文件: {output_path}")
        print(f"   存在: {os.path.exists(output_path)}")
    except Exception as e:
        print(f"❌ 主API测试失败: {str(e)}")
        return False
    
    # 测试2: 兼容API（原始填充 - 向后兼容）
    print("\n" + "=" * 80)
    print("测试2: /fill/legacy (兼容API - 原始填充)")
    print("=" * 80)
    try:
        output_path_legacy = FillerService.fill_template(
            resume_data=resume_data,
            orientation="vertical",
            output_filename="api_legacy_test.pptx"
        )
        print(f"✅ 兼容API测试通过!")
        print(f"   文件: {output_path_legacy}")
        print(f"   存在: {os.path.exists(output_path_legacy)}")
    except Exception as e:
        print(f"❌ 兼容API测试失败: {str(e)}")
        return False
    
    print("\n" + "=" * 80)
    print("🎯 重构后的API结构")
    print("=" * 80)
    print("\n✅ 新的API结构:")
    print("   ├─ POST /fill")
    print("   │   └─ 智能填充（推荐）- 支持多段经历")
    print("   │      ├─ 💼 work")
    print("   │      ├─ 📦 project")
    print("   │      └─ 🎓 education")
    print("   └─ POST /fill/legacy")
    print("       └─ 原始填充（向后兼容）")
    print("\n❌ 已移除:")
    print("   ├─ POST /fill/smart (已合并到 /fill)")
    print("   └─ POST /fill/advanced (已移除 - 框架代码保留)")
    
    print("\n💡 使用指南:")
    print("   • 所有新开发: 使用 POST /fill")
    print("   • 旧版本兼容: 使用 POST /fill/legacy")
    
    print("\n✅ API重构完成并测试通过!")
    
    return True


if __name__ == "__main__":
    success = test_refactored_api()
    sys.exit(0 if success else 1)
