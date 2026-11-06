"""验证 skill 全局占位符（{{tech_skills}}/{{lang_skills}}/{{lang_skills_level}}）填充修复"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pptx import Presentation
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.smart_filler_service import SmartFillerService

OUTPUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                      'output', '_verify_skill_fill.pptx')

resume = ResumeData(
    name="赵工",
    anonymized_name="Mr.Zhao",
    position="测试验证及标定工程师",
    technical_area="动力总成",
    total_exp="13年",
    summary="负责动力总成测试验证。",
    tech_skills="INCA测试软件； MDA分析； 熟悉发动机构造",
    lang_skills="英语",
    lang_skills_level="CET6;读写精通",
    training_exp="",
    language="CN",
    education=[
        EducationItem(period="2010.09-2012.07", school="吉林大学", degree="硕士", major="车辆工程"),
        EducationItem(period="2006.09-2010.07", school="吉林大学", degree="本科", major="车辆工程"),
    ],
    work=[
        WorkItem(company="北京现代汽车有限公司", period="2012.07-至今", role="测试验证及标定工程师",
                 tasks="验证标定试制阶段车辆不同EMS数据，涉及整车油耗、排放、OBD及三高试验；\n排查解决相关车型生命周期内动力总成故障；\n处理强检认证试验期间的各类车辆故障"),
    ],
    project=[
        ProjectItem(company="北京现代汽车有限公司", period="2018.09-至今", name="新车型认证项目", role="车型负责人",
                    tasks="制定新车型动力总成相关性能参数；\n制定评价验证试验计划；\n应对强检认证试验中的突发问题"),
    ],
)

result = SmartFillerService.fill_template(resume, template_type=None, orientation='vertical', generate_pdf=False)
print("\n生成完成:", result["pptx_path"])

# 检查输出 skill 表格
prs = Presentation(result["pptx_path"])
for si, slide in enumerate(prs.slides):
    for shape in slide.shapes:
        if shape.has_table:
            for ri, row in enumerate(shape.table.rows):
                texts = [c.text.replace('\n', '|') for c in row.cells]
                joined = ' '.join(texts)
                if '能力' in joined or '语言' in joined or 'tech_skills' in joined or 'lang_skills' in joined:
                    print(f"--- 第{si+1}页 skill 表格 R{ri}: {texts}")

# 断言
ok = False
for si, slide in enumerate(prs.slides):
    for shape in slide.shapes:
        if shape.has_table:
            for ri, row in enumerate(shape.table.rows):
                cell_text = ' '.join(c.text for c in row.cells)
                if '能力' in cell_text:
                    assert 'INCA测试软件' in cell_text, f"tech_skills 未填充! 实际: {cell_text}"
                    assert '英语' in cell_text, f"lang_skills 未填充! 实际: {cell_text}"
                    assert 'CET6' in cell_text, f"lang_skills_level 未填充! 实际: {cell_text}"
                    assert '{{' not in cell_text, f"残留占位符! 实际: {cell_text}"
                    ok = True
                    print("\n✅ skill 字段全部正确填充")

assert ok, "未找到 skill 表格行"
print("✅ 验证通过")
