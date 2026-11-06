"""
测试高级智能填充服务 - 包含大量工作经历测试分页
"""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.advanced_smart_filler import SmartFillerService
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.template_config import TemplateType


def test_many_work_experiences():
    """测试大量工作经历 - 验证分页潜力"""
    
    print("=" * 80)
    print("测试高级智能填充 - 大量工作经历")
    print("=" * 80)
    
    resume_data = ResumeData(
        name="王五",
        position="资深技术专家",
        technical_area="全栈开发",
        total_exp="15年",
        tech_skills="Python, Java, Go, React, AWS, Docker, Kubernetes",
        lang_skills="中文(母语), English(流利), 日语(日常)",
        lang_skills_level="高级",
        training_exp="AWS认证架构师\nKubernetes管理员认证",
        language="CN",
        
        work=[
            WorkItem(
                company="科技巨头A",
                period="2021.03-至今",
                role="技术总监",
                tasks="负责50人团队管理\n制定技术路线图\n产品架构设计\n核心系统开发\n跨部门协调\n人才培养"
            ),
            WorkItem(
                company="创业公司B",
                period="2018.07-2021.02",
                role="技术合伙人",
                tasks="从0到1搭建技术团队\n选择技术栈\n开发MVP产品\n融资路演技术支持\n产品迭代优化"
            ),
            WorkItem(
                company="互联网公司C",
                period="2016.06-2018.06",
                role="高级架构师",
                tasks="系统架构设计\n微服务改造\n性能优化\n技术团队搭建"
            ),
            WorkItem(
                company="软件公司D",
                period="2013.03-2016.05",
                role="技术负责人",
                tasks="带领10人团队\n敏捷开发实践\nCI/CD搭建\n代码评审"
            ),
            WorkItem(
                company="IT公司E",
                period="2010.07-2013.02",
                role="高级开发工程师",
                tasks="核心模块开发\n数据库优化\n新人培训\n技术文档"
            ),
            WorkItem(
                company="外企F",
                period="2008.09-2010.06",
                role="开发工程师",
                tasks="功能开发\nBug修复\n单元测试\n项目上线支持"
            ),
        ],
        
        project=[
            ProjectItem(
                company="科技巨头A",
                period="2022.01-2023.12",
                name="超级平台项目",
                role="架构师",
                tasks="设计高可用架构\n千万级用户支持\n微服务设计\nDevOps体系"
            ),
            ProjectItem(
                company="创业公司B",
                period="2019.05-2020.11",
                name="电商平台",
                role="技术负责人",
                tasks="全栈开发\n支付系统\n物流对接\n订单系统"
            ),
        ],
        
        education=[
            EducationItem(
                period="2006.09-2008.06",
                school="名牌大学研究生院",
                degree="硕士",
                major="计算机科学"
            ),
            EducationItem(
                period="2002.09-2006.06",
                school="重点大学",
                degree="本科",
                major="软件工程"
            ),
        ]
    )
    
    print("\n📋 测试数据:")
    print(f"   姓名: {resume_data.name}")
    print(f"   工作经历: {len(resume_data.work)} 条 (较多)")
    print(f"   项目经历: {len(resume_data.project)} 条")
    print(f"   教育经历: {len(resume_data.education)} 条")
    
    print("\n" + "=" * 80)
    print("🚀 开始高级智能填充...")
    print("=" * 80)
    
    try:
        output_path = SmartFillerService.fill_template(
            resume_data=resume_data,
            template_type=TemplateType.NEW_CN,
            output_filename="advanced_filler_test.pptx"
        )
        
        print(f"\n✅ 填充成功!")
        print(f"📁 输出文件: {output_path}")
        print(f"📄 文件存在: {os.path.exists(output_path)}")
        
        if os.path.exists(output_path):
            file_size = os.path.getsize(output_path)
            print(f"📊 文件大小: {file_size / 1024:.2f} KB")
        
        print("\n" + "=" * 80)
        print("🎯 功能说明:")
        print("=" * 80)
        print("\n✅ 已实现的核心功能:")
        print("   1. 自动克隆表格行 - 根据工作经历数量")
        print("   2. 逐条填充 - 每条经历填对应行")
        print("   3. 自动调整行高 - 根据内容多少")
        print("\n⏳ 高级分页功能说明:")
        print("   完整的自动分页需要更复杂的实现，")
        print("   包括:")
        print("   - 精确计算内容高度")
        print("   - 动态创建新幻灯片")
        print("   - 表格跨页拆分")
        print("   - 布局重新计算")
        print("\n💡 当前方案:")
        print("   已提供完整框架，可根据实际需求")
        print("   进一步定制开发！")
        
        print("\n📝 请打开生成的PPT查看效果!")
        print(f"   文件: {output_path}")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 填充失败: {str(e)}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_many_work_experiences()
    sys.exit(0 if success else 1)
