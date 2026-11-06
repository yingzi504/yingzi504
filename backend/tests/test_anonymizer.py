"""
测试脱敏服务
验证 Pipeline 步骤 3 的脱敏功能
"""
import asyncio
import sys
import os
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem
from app.services.anonymizer_service import AnonymizerService


def test_anonymize_resume():
    """测试简历脱敏"""
    print("=" * 60)
    print("测试: 简历脱敏")
    print("=" * 60)
    
    # 创建测试简历数据
    test_resume = ResumeData(
        name="张伟",
        phone="13800138000",
        email="zhangwei@example.com",
        age=28,
        birth_date="1995-05-15",
        location="北京市朝阳区",
        position="Python开发工程师",
        technical_area="人工智能",
        total_exp="5年",
        summary="具有5年Python开发经验，擅长机器学习和数据分析，参与过多个大型项目。",
        tech_skills="Python, TensorFlow, PyTorch, SQL, Docker",
        lang_skills="英语, 日语",
        education=[
            EducationItem(
                period="2015-2019",
                school="清华大学",
                degree="学士",
                major="计算机科学"
            )
        ],
        work=[
            WorkItem(
                company="阿里巴巴",
                period="2019-2022",
                role="软件工程师",
                tasks="负责后端开发和机器学习模型部署"
            ),
            WorkItem(
                company="腾讯",
                period="2022-2024",
                role="高级软件工程师",
                tasks="负责系统架构设计"
            )
        ],
        project=[
            ProjectItem(
                company="阿里巴巴",
                period="2021-2022",
                name="智能推荐系统",
                role="核心开发者",
                tasks="设计和实现推荐算法，提升用户留存率"
            ),
            ProjectItem(
                company="百度",
                period="2023-2024",
                name="自动驾驶平台",
                role="技术负责人",
                tasks="负责平台核心模块开发"
            )
        ],
        language="CN"
    )
    
    print("\n原始简历:")
    print(f"  姓名: {test_resume.name}")
    print(f"  电话: {test_resume.phone}")
    print(f"  邮箱: {test_resume.email}")
    print(f"  年龄: {test_resume.age}")
    print(f"  生日: {test_resume.birth_date}")
    print(f"  地址: {test_resume.location}")
    print(f"  工作经历公司: {[w.company for w in test_resume.work]}")
    print(f"  项目经历公司: {[p.company for p in test_resume.project]}")
    
    try:
        anonymized = AnonymizerService.anonymize_resume(test_resume)
        print("\n脱敏后简历:")
        print(f"  姓名: {anonymized.name}")
        print(f"  电话: {anonymized.phone}")
        print(f"  邮箱: {anonymized.email}")
        print(f"  年龄: {anonymized.age}")
        print(f"  生日: {anonymized.birth_date}")
        print(f"  地址: {anonymized.location}")
        print(f"  工作经历公司: {[w.company for w in anonymized.work]}")
        print(f"  项目经历公司: {[p.company for p in anonymized.project]}")
        print(f"  是否已脱敏: {anonymized.is_anonymized}")
        
        # 验证脱敏结果
        assert anonymized.phone is None, "电话应该被移除"
        assert anonymized.email is None, "邮箱应该被移除"
        assert anonymized.age is None, "年龄应该被移除"
        assert anonymized.birth_date is None, "生日应该被移除"
        assert anonymized.location is None, "地址应该被移除"
        assert anonymized.is_anonymized is True, "应该标记为已脱敏"
        assert "Mr./Ms." in anonymized.name, "姓名应该脱敏"
        assert "Company A" in [w.company for w in anonymized.work], "公司名应该被映射"
        
        print("\n✅ 所有验证通过!")
        return anonymized
    except AssertionError as e:
        print(f"\n❌ 验证失败: {e}")
        return None
    except Exception as e:
        print(f"\n❌ 脱敏失败: {e}")
        return None


async def main():
    """主测试函数"""
    print("\n" + "=" * 60)
    print("脱敏服务测试")
    print("=" * 60)
    
    test_anonymize_resume()
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
