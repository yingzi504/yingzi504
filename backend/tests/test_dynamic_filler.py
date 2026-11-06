"""
测试动态填充多行工作经历
"""
import os
import sys
import tempfile

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.filler_service import FillerService
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.template_config import TemplateType


def test_dynamic_filler():
    """测试动态填充多行工作经历"""
    
    # 1. 创建测试数据 - 包含多个工作经历
    resume_data = ResumeData(
        name="张三",
        position="高级软件工程师",
        technical_area="人工智能",
        total_exp="10年",
        tech_skills="Python, Java, C++",
        lang_skills="中文(母语), English(流利)",
        lang_skills_level="高级",
        training_exp="无",
        language="CN",
        
        # 工作经历 - 3条
        work=[
            WorkItem(
                company="科技公司A",
                period="2020.01-2023.12",
                role="软件工程师",
                tasks="负责产品开发和系统设计"
            ),
            WorkItem(
                company="科技公司B",
                period="2018.06-2019.12",
                role="初级工程师",
                tasks="参与系统开发"
            ),
            WorkItem(
                company="科技公司C",
                period="2015.03-2018.05",
                role="实习生",
                tasks="学习软件开发"
            )
        ],
        
        # 项目经历 - 2条
        project=[
            ProjectItem(
                company="科技公司A",
                period="2021.01-2022.12",
                name="智能客服系统",
                role="主程",
                tasks="负责核心系统开发"
            ),
            ProjectItem(
                company="科技公司B",
                period="2018.07-2019.06",
                name="内部管理系统",
                role="参与开发",
                tasks="开发部分功能模块"
            )
        ],
        
        # 教育经历 - 1条
        education=[
            EducationItem(
                period="2011.09-2015.06",
                school="XX大学",
                degree="本科",
                major="计算机科学与技术"
            )
        ]
    )
    
    print("=" * 80)
    print("测试动态填充多行工作经历")
    print("=" * 80)
    print(f"\n输入数据:")
    print(f"  - 工作经历数量: {len(resume_data.work)}")
    print(f"  - 项目经历数量: {len(resume_data.project)}")
    print(f"  - 教育经历数量: {len(resume_data.education)}")
    print("\n工作经历:")
    for i, work in enumerate(resume_data.work):
        print(f"  [{i}] {work.company} - {work.role}")
    
    # 2. 测试构建替换字典
    print("\n" + "=" * 80)
    print("1. 测试构建替换字典")
    print("=" * 80)
    
    resume_dict = resume_data.model_dump()
    replacements = FillerService.build_replacements(resume_dict)
    
    print(f"\n生成的替换字典数量: {len(replacements)}")
    
    print("\n基础字段替换:")
    for key in ["{{name}}", "{{position}}", "{{technical_area}}"]:
        print(f"  {key} = '{replacements.get(key, 'NOT FOUND')}'")
    
    print("\n工作经历替换:")
    for i in range(len(resume_data.work)):
        print(f"\n  索引 {i}:")
        for field in ["company", "period", "role", "tasks"]:
            key = f"{{{{work{i}.{field}}}}}"
            print(f"    {key} = '{replacements.get(key, 'NOT FOUND')}'")
    
    print("\n项目经历替换:")
    for i in range(len(resume_data.project)):
        print(f"\n  索引 {i}:")
        for field in ["company", "period", "name", "role"]:
            key = f"{{{{project{i}.{field}}}}}"
            print(f"    {key} = '{replacements.get(key, 'NOT FOUND')}'")
    
    # 3. 验证所有替换是否正确
    print("\n" + "=" * 80)
    print("2. 验证替换字典")
    print("=" * 80)
    
    all_correct = True
    
    # 验证工作经历
    for i in range(len(resume_data.work)):
        expected = resume_data.work[i].company
        actual = replacements.get(f"{{{{work{i}.company}}}}")
        if actual == expected:
            print(f"  ✓ work[{i}].company: '{actual}'")
        else:
            print(f"  ✗ work[{i}].company: 期望 '{expected}', 实际 '{actual}'")
            all_correct = False
    
    # 验证项目经历
    for i in range(len(resume_data.project)):
        expected = resume_data.project[i].name
        actual = replacements.get(f"{{{{project{i}.name}}}}")
        if actual == expected:
            print(f"  ✓ project[{i}].name: '{actual}'")
        else:
            print(f"  ✗ project[{i}].name: 期望 '{expected}', 实际 '{actual}'")
            all_correct = False
    
    # 4. 测试占位符格式
    print("\n" + "=" * 80)
    print("3. 支持的占位符格式")
    print("=" * 80)
    print("\n工作经历:")
    print("  - {{work.company}}  (第一条记录)")
    print("  - {{work0.company}} (第一条记录)")
    print("  - {{work1.company}} (第二条记录)")
    print("  - {{work2.company}} (第三条记录)")
    print("\n项目经历:")
    print("  - {{project.name}}  (第一条记录)")
    print("  - {{project0.name}} (第一条记录)")
    print("  - {{project1.name}} (第二条记录)")
    print("\n教育经历:")
    print("  - {{education.school}}  (第一条记录)")
    print("  - {{education0.school}} (第一条记录)")
    
    print("\n" + "=" * 80)
    print("测试完成")
    print("=" * 80)
    
    if all_correct:
        print("\n✅ 所有测试通过！")
        return True
    else:
        print("\n❌ 部分测试失败！")
        return False


if __name__ == "__main__":
    success = test_dynamic_filler()
    sys.exit(0 if success else 1)
