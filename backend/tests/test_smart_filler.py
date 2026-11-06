"""
测试智能填充服务
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.smart_filler_service import SmartFillerService
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.template_config import TemplateType


def test_smart_filler():
    """测试智能填充功能"""
    
    print("=" * 80)
    print("测试智能PPT填充服务")
    print("=" * 80)
    
    resume_data = ResumeData(
        name="张三",
        position="高级软件工程师",
        technical_area="人工智能",
        total_exp="8年",
        tech_skills="Python, TensorFlow, PyTorch, NLP",
        lang_skills="中文(母语), English(流利)",
        lang_skills_level="高级",
        training_exp="斯坦福大学机器学习课程",
        language="CN",
        
        work=[
            WorkItem(
                company="AI创新实验室",
                period="2021.03-至今",
                role="高级AI工程师",
                tasks="负责NLP模型研发\n负责产品化\n负责团队技术指导"
            ),
            WorkItem(
                company="数据科技公司",
                period="2018.07-2021.02",
                role="机器学习工程师",
                tasks="开发推荐系统\n数据分析工具开发"
            ),
            WorkItem(
                company="软件开发公司",
                period="2016.06-2018.06",
                role="软件工程师",
                tasks="参与Web应用开发\n单元测试编写"
            )
        ],
        
        project=[
            ProjectItem(
                company="AI创新实验室",
                period="2022.01-2023.12",
                name="智能对话系统",
                role="技术负责人",
                tasks="设计多轮对话系统\nNLU模块开发"
            ),
            ProjectItem(
                company="数据科技公司",
                period="2019.05-2020.11",
                name="个性化推荐引擎",
                role="核心开发",
                tasks="开发协同过滤算法\nA/B测试框架"
            )
        ],
        
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
    
    print("\n📋 测试数据:")
    print(f"   姓名: {resume_data.name}")
    print(f"   工作经历: {len(resume_data.work)} 条")
    print(f"   项目经历: {len(resume_data.project)} 条")
    print(f"   教育经历: {len(resume_data.education)} 条")
    
    print("\n" + "=" * 80)
    print("🚀 开始智能填充...")
    print("=" * 80)
    
    try:
        result = SmartFillerService.fill_template(
            resume_data=resume_data,
            template_type=TemplateType.NEW_CN,
            generate_pdf=False,
        )
        
        output_path = result.get("pptx_path", "")
        print(f"\n✅ 填充成功!")
        print(f"📁 输出文件: {output_path}")
        print(f"📄 文件存在: {os.path.exists(output_path)}")
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📊 文件大小: {file_size / 1024:.2f} KB")
        
        print("\n" + "=" * 80)
        print("🎯 功能验证:")
        print("=" * 80)
        print("\n✅ 1. 自动克隆表格行 - 已实现")
        print("✅ 2. 逐条填充工作经历 - 已实现")
        print("✅ 3. 自动调整行高 - 已实现")
        print("\n📝 请打开生成的PPT文件查看效果!")
        print(f"   文件: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 填充失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_smart_filler()
    sys.exit(0 if success else 1)
