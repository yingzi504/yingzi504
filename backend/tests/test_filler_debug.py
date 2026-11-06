"""
快速调试测试 - 直接测试SmartFillerService.fill_template()的多条目填充
"""
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.smart_filler_service import SmartFillerService
from app.services.template_config import TemplateType

def main():
    print("=" * 70)
    print("测试：SmartFillerService 多条目填充")
    print("=" * 70)
    
    # 创建5条工作经历 + 5条项目经历（模拟用户上传的真实简历）
    test_resume = ResumeData(
        name="Mr. Zhang",
        anonymized_name="Mr. Zhang",
        phone="13800138000",
        email="zhangwei@example.com",
        location="Beijing",
        position="Software Engineer",
        technical_area="AI/ML",
        total_exp="5 years",
        summary="具有5年Python开发经验",
        tech_skills="Python, TensorFlow, SQL",
        lang_skills="English",
        lang_skills_level="Fluent",
        training_exp="ML Certification",
        education=[
            EducationItem(
                period="2015-2019",
                school="Tsinghua University",
                degree="Bachelor",
                major="Computer Science"
            )
        ],
        work=[
            WorkItem(
                company="Company A",
                period="2024-2025",
                role="Senior Engineer",
                tasks="负责AI算法研发和模型优化"
            ),
            WorkItem(
                company="Company B",
                period="2023-2024",
                role="Software Engineer",
                tasks="负责后端微服务开发"
            ),
            WorkItem(
                company="Company C",
                period="2022-2023",
                role="Backend Developer",
                tasks="负责API设计和数据库优化"
            ),
            WorkItem(
                company="Company D",
                period="2021-2022",
                role="Junior Developer",
                tasks="负责前端页面开发"
            ),
            WorkItem(
                company="Company E",
                period="2020-2021",
                role="Intern",
                tasks="参与自动化测试工具开发"
            ),
        ],
        project=[
            ProjectItem(
                company="Company A",
                period="2024-2025",
                name="AI Platform",
                role="Core Developer",
                tasks="设计深度学习推理框架"
            ),
            ProjectItem(
                company="Company B",
                period="2023-2024",
                name="Recommendation System",
                role="Developer",
                tasks="实现实时推荐算法"
            ),
            ProjectItem(
                company="Company C",
                period="2022-2023",
                name="Data Platform",
                role="Developer",
                tasks="建设大数据处理平台"
            ),
            ProjectItem(
                company="Company D",
                period="2021-2022",
                name="Web Dashboard",
                role="Frontend Dev",
                tasks="开发数据可视化面板"
            ),
            ProjectItem(
                company="Company E",
                period="2020-2021",
                name="Test Automation",
                role="Intern",
                tasks="开发自动化测试脚本"
            ),
        ],
        language="CN",
        is_anonymized=True
    )
    
    print("\n测试简历数据:")
    print(f"  姓名: {test_resume.name}")
    print(f"  职位: {test_resume.position}")
    print(f"  工作经历: {len(test_resume.work)} 条")
    for i, w in enumerate(test_resume.work):
        print(f"    work[{i}]: {w.company} | {w.period} | {w.role}")
    print(f"  项目经历: {len(test_resume.project)} 条")
    for i, p in enumerate(test_resume.project):
        print(f"    project[{i}]: {p.company} | {p.name} | {p.role}")
    print(f"  教育经历: {len(test_resume.education)} 条")
    
    print(f"\n{'='*70}")
    print(f"调用 SmartFillerService.fill_template()...")
    print(f"{'='*70}\n")
    
    try:
        result = SmartFillerService.fill_template(
            resume_data=test_resume,
            template_type=TemplateType.NEW_CN,
            generate_pdf=False,
        )
        
        print(f"\n{'='*70}")
        print(f"填充完成!")
        print(f"{'='*70}")
        print(f"PPTX路径: {result['pptx_path']}")
        print(f"文件名: {result['filename']}")
        
        # 验证输出PPTX
        from pptx import Presentation
        prs = Presentation(result['pptx_path'])
        print(f"\n输出PPTX分析:")
        print(f"  总页数: {len(prs.slides)}")
        
        for si, slide in enumerate(prs.slides):
            print(f"\n  === Slide {si+1} ===")
            for shape in slide.shapes:
                if shape.has_table:
                    table = shape.table
                    print(f"    表格: {len(table.rows)}行 x {len(table.columns)}列")
                    for ri, row in enumerate(table.rows):
                        texts = []
                        for cell in row.cells:
                            txt = cell.text.strip()[:120].replace('\n', ' | ')
                            if len(txt) > 100:
                                txt = txt[:100] + '...'
                            texts.append(txt)
                        print(f"      Row {ri}: {texts}")
                elif hasattr(shape, 'text_frame'):
                    txt = shape.text_frame.text.strip()[:120]
                    if txt:
                        print(f"      Text: {txt.replace(chr(10), ' ')}")
    
    except Exception as e:
        print(f"\n❌ 错误: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
