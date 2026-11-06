"""
直接测试 SmartFillerService - 使用模拟数据测试文件名、职责分点、内容重复
测试流水线: Pipeline步骤 6 的直接调用
"""

import os, sys, json, re
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem

# ========== 模拟数据定义 ==========

# 中文简历数据
cn_data = ResumeData(
    name="张伟",
    anonymized_name="张先生",
    anonymized_name_cn="张先生",
    gender="male",
    position="高级软件工程师",
    language="CN",
    phone="13800138000",
    email="zhangwei@example.com",
    technical_area="软件开发",
    total_exp="10年",
    tech_skills="Python, Java, C++",
    lang_skills="中文, English",
    lang_skills_level="母语, 流利",
    training_exp="PMP认证",
    summary="10年软件开发经验",
    work=[
        WorkItem(
            company="ABC科技有限公司",
            period="2020.01 - 至今",
            role="高级工程师",
            tasks="• 负责核心模块架构设计与开发\n• 优化系统性能，提升响应速度30%\n• 带领5人团队完成项目交付"
        ),
        WorkItem(
            company="XYZ信息技术公司",
            period="2017.06 - 2019.12",
            role="软件工程师",
            tasks="• 参与电商平台后端开发\n• 编写单元测试和集成测试\n• 维护线上系统稳定运行"
        ),
        WorkItem(
            company="DEF科技",
            period="2015.09 - 2017.05",
            role="初级工程师",
            tasks="• 负责前端页面开发\n• 参与数据库设计\n• 编写技术文档"
        )
    ],
    project=[
        ProjectItem(
            company="ABC科技有限公司",
            period="2021.01 - 2021.12",
            name="智能运维平台",
            role="技术负责人",
            tasks="• 设计微服务架构\n• 实现自动化部署流水线\n• 编写技术方案文档"
        )
    ],
    education=[
        EducationItem(
            period="2011.09 - 2015.07",
            school="北京理工大学",
            degree="本科",
            major="计算机科学与技术"
        )
    ]
)

# 英文简历数据
en_data = ResumeData(
    name="张伟",
    anonymized_name="Mr.Zhang",
    anonymized_name_cn="张先生",
    gender="male",
    position="Senior Software Engineer",
    language="EN",
    phone="13800138000",
    email="zhangwei@example.com",
    technical_area="Software Development",
    total_exp="10 years",
    tech_skills="Python, Java, C++",
    lang_skills="Chinese, English",
    lang_skills_level="Native, Fluent",
    training_exp="PMP Certified",
    summary="10 years of software development experience",
    work=[
        WorkItem(
            company="ABC Technology Co., Ltd.",
            period="2020.01 - Present",
            role="Senior Engineer",
            tasks="• Designed and developed core modules\n• Optimized system performance, improving response time by 30%\n• Led a team of 5 engineers"
        ),
        WorkItem(
            company="XYZ Information Technology",
            period="2017.06 - 2019.12",
            role="Software Engineer",
            tasks="• Backend development for e-commerce platform\n• Wrote unit tests and integration tests\n• Maintained production system stability"
        )
    ],
    project=[
        ProjectItem(
            company="ABC Technology Co., Ltd.",
            period="2021.01 - 2021.12",
            name="Intelligent Operations Platform",
            role="Tech Lead",
            tasks="• Designed microservice architecture\n• Implemented CI/CD pipeline\n• Authored technical design documents"
        )
    ],
    education=[
        EducationItem(
            period="2011.09 - 2015.07",
            school="Beijing Institute of Technology",
            degree="Bachelor",
            major="Computer Science"
        )
    ]
)


def run_filler_demo(data: ResumeData, label: str):
    """测试 SmartFillerService.fill_template"""
    from app.services.smart_filler_service import SmartFillerService
    
    print(f"\n{'='*70}")
    print(f"  测试: {label}")
    print(f"{'='*70}")
    print(f"  语言: {data.language}")
    print(f"  anonymized_name: {data.anonymized_name}")
    print(f"  anonymized_name_cn: {data.anonymized_name_cn}")
    print(f"  position: {data.position}")
    print(f"  work条目数: {len(data.work)}")
    for i, w in enumerate(data.work):
        print(f"    work[{i}].tasks = {repr(w.tasks[:50])}..." if w.tasks else f"    work[{i}].tasks = None")
    
    try:
        result = SmartFillerService.fill_template(
            data,
            orientation='vertical',
            generate_pdf=False,
        )
        
        print(f"\n  ✅ 填充成功!")
        print(f"  文件名: {result['filename']}")
        print(f"  PPTX路径: {result['pptx_path']}")
        
        # 检查文件名
        expected_lang = 'CN' if data.language == 'CN' else 'EN'
        if f'IAV_' in result['filename'] and f'Resume_{expected_lang}' in result['filename']:
            print(f"  ✅ 文件名格式正确!")
        else:
            print(f"  ❌ 文件名格式可能有问题!")
        
        # 检查PPT内容
        from pptx import Presentation
        prs = Presentation(result['pptx_path'])
        print(f"  总页数: {len(prs.slides)}")
        
        # 提取所有文本检查
        all_text = []
        for si, slide in enumerate(prs.slides):
            slide_texts = []
            for shape in slide.shapes:
                if hasattr(shape, 'text') and shape.text.strip():
                    slide_texts.append(shape.text.strip())
                if shape.has_table:
                    for ri, row in enumerate(shape.table.rows):
                        for ci, cell in enumerate(row.cells):
                            text = cell.text.strip()
                            if text:
                                slide_texts.append(f"  [表{ri},{ci}] {text}")
            all_text.append((si, slide_texts))
        
        # 检查bullet points (•)
        full_text = '\n'.join(['\n'.join(t[1]) for t in all_text])
        
        # 检查每个work条目的tasks是否都有•前缀
        bullet_count = full_text.count('•')
        print(f"  总bullet • 出现次数: {bullet_count}")
        
        # 检查是否有未替换的占位符
        placeholders_remaining = re.findall(r'\{\{[\w.]+\}\}', full_text)
        if placeholders_remaining:
            print(f"  ❌ 发现未替换的占位符: {placeholders_remaining}")
        else:
            print(f"  ✅ 没有未替换的占位符")
        
        # 检查是否有重复内容（同一个tasks出现多次应合理）
        # 检查不同的work条目是否有各自的任务内容
        for i, w in enumerate(data.work):
            if w.tasks:
                # 取第一行任务
                first_task = w.tasks.split('\n')[0].strip()
                count = full_text.count(first_task[2:])  # 去掉•前缀
                if count > 1:
                    print(f"  ⚠️  work[{i}] '{first_task[:30]}...' 出现了{count}次")
                else:
                    print(f"  ✅  work[{i}] 任务内容唯一出现")
        
        # 检查每个work条目的公司名
        for i, w in enumerate(data.work):
            if w.company:
                company_count = full_text.count(w.company)
                if company_count >= 1:
                    print(f"  ✅  '{w.company}' 出现{company_count}次")
                else:
                    print(f"  ❌  '{w.company}' 未出现!")
        
        print(f"")
        return result
        
    except Exception as e:
        print(f"\n  ❌ 失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return None


if __name__ == '__main__':
    print("=" * 70)
    print("  SmartFillerService 直接填充测试")
    print("  测试项: 文件名格式 / bullet分点 / 内容重复")
    print("=" * 70)
    
    # 测试中文
    r1 = run_filler_demo(cn_data, "中文简历 CN")
    
    # 测试英文
    r2 = run_filler_demo(en_data, "英文简历 EN")
    
    print("\n" + "=" * 70)
    print("  测试完成!")
    if r1 and r2:
        print(f"  CN文件名: {r1['filename']}")
        print(f"  EN文件名: {r2['filename']}")
    print("=" * 70)
