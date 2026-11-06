"""
演示如果模板修改好了，代码是如何完美工作的
"""
import os
import sys

# 添加项目路径
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.filler_service import FillerService
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.template_config import TemplateType


def demo_with_simulated_template():
    """模拟模板已修改的场景"""
    
    print("=" * 80)
    print("演示：如果模板已修改为带索引占位符")
    print("=" * 80)
    
    # 创建测试数据
    resume_data = ResumeData(
        name="张三",
        position="高级软件工程师",
        technical_area="人工智能",
        total_exp="8年",
        tech_skills="Python, TensorFlow, PyTorch",
        lang_skills="中文, English",
        lang_skills_level="高级",
        training_exp="机器学习课程",
        language="CN",
        
        # 3条工作经历
        work=[
            WorkItem(
                company="AI创新实验室",
                period="2021.03-至今",
                role="高级AI工程师",
                tasks="负责NLP模型研发"
            ),
            WorkItem(
                company="数据科技公司",
                period="2018.07-2021.02",
                role="机器学习工程师",
                tasks="开发推荐系统"
            ),
            WorkItem(
                company="软件开发公司",
                period="2016.06-2018.06",
                role="软件工程师",
                tasks="参与Web应用开发"
            )
        ],
        
        # 2条项目经历
        project=[
            ProjectItem(
                company="AI创新实验室",
                period="2022.01-2023.12",
                name="智能对话系统",
                role="技术负责人",
                tasks="设计多轮对话系统"
            ),
            ProjectItem(
                company="数据科技公司",
                period="2019.05-2020.11",
                name="个性化推荐引擎",
                role="核心开发",
                tasks="开发协同过滤算法"
            )
        ],
        
        # 2条教育经历
        education=[
            EducationItem(
                period="2013.09-2016.06",
                school="XX大学研究生院",
                degree="硕士",
                major="计算机应用技术"
            ),
            EducationItem(
                period="2009.09-2013.06",
                school="YY大学",
                degree="本科",
                major="软件工程"
            )
        ]
    )
    
    resume_dict = resume_data.model_dump()
    
    # 演示替换字典是如何构建的
    print("\n1. 构建替换字典:")
    print("-" * 80)
    
    replacements = FillerService.build_replacements(resume_dict)
    
    print("\n工作经历替换:")
    for i in range(3):
        print(f"\n  [第{i+1}条]")
        print(f"    {{work{i}.company}} = {replacements.get(f'{{work{i}.company}}', 'N/A')}")
        print(f"    {{work{i}.period}} = {replacements.get(f'{{work{i}.period}}', 'N/A')}")
        print(f"    {{work{i}.role}} = {replacements.get(f'{{work{i}.role}}', 'N/A')}")
    
    print("\n项目经历替换:")
    for i in range(2):
        print(f"\n  [第{i+1}条]")
        print(f"    {{project{i}.name}} = {replacements.get(f'{{project{i}.name}}', 'N/A')}")
    
    print("\n教育经历替换:")
    for i in range(2):
        print(f"\n  [第{i+1}条]")
        print(f"    {{education{i}.school}} = {replacements.get(f'{{education{i}.school}}', 'N/A')}")
    
    print("\n" + "=" * 80)
    print("2. 如果模板中有这些占位符:")
    print("=" * 80)
    print("\n工作经历区域:")
    print("  第1行: {{work0.company}} {{work0.period}} {{work0.role}}")
    print("  第2行: {{work1.company}} {{work1.period}} {{work1.role}}")
    print("  第3行: {{work2.company}} {{work2.period}} {{work2.role}}")
    print("\n填充结果会是:")
    print("  第1行: AI创新实验室 2021.03-至今 高级AI工程师")
    print("  第2行: 数据科技公司 2018.07-2021.02 机器学习工程师")
    print("  第3行: 软件开发公司 2016.06-2018.06 软件工程师")
    
    print("\n" + "=" * 80)
    print("总结")
    print("=" * 80)
    print("\n✅ 代码已经完全支持多行填充")
    print("✅ 只需要在PPT模板中:")
    print("   1. 复制粘贴创建多行")
    print("   2. 占位符加上索引 (0, 1, 2...)")
    print("\n📖 详细步骤请参考: docs/模板分步修改指南.md")


if __name__ == "__main__":
    demo_with_simulated_template()
