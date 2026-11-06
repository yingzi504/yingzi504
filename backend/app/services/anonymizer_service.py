"""
脱敏服务
处理个人敏感信息
"""
import re
import traceback
from pypinyin import lazy_pinyin
from typing import Dict, Any, Optional
from fastapi import HTTPException
from app.schemas.resume import ResumeData, WorkItem, ProjectItem, EducationItem


# ── 性别推断：基于中文名字中常见字的特征 ──
# 注意：这只是一个启发式规则，不是100%准确
_FEMALE_NAME_CHARS = set(
    '芳丽娟敏静艳霞秀英慧琳玲琴婷梅雪萍红兰菊燕花娜蓉芬莹莉云丹君'
    '彩洁虹雯婉瑶璐薇芙菁荷萱婵琳玲莉柔媚姑妙妃婷菲婉媛雅'
)
_MALE_NAME_CHARS = set(
    '伟强军平刚杰涛磊洋勇明华龙林国建坤峰超宁飞毅永德辉义'
    '志鹏宇浩博文亮斌东旭海瑞凯健恒子轩'
)


class AnonymizerService:
    """脱敏服务"""
    
    @staticmethod
    def _infer_gender(name: str) -> str:
        """
        根据中文姓名推断性别

        策略（按优先级）：
        1. 名字中包含敬称后缀（女士/先生/Mr./Ms.等）→ 直接返回对应性别
        2. 去掉敬称后，名字中包含女性常用字（不包含男性常用字）→ female
        3. 名字中包含男性常用字（不包含女性常用字）→ male
        4. 默认 → male（行业惯例使用先生）

        Args:
            name: 中文姓名（如 "卢女士", "张三", "Ms. Li"）

        Returns:
            "male" 或 "female"
        """
        if not name or len(name) < 1:
            return "male"

        # ── 策略1：敬称直接检测 ──
        name_stripped = name.strip()

        # 中文敬称是后缀：如 "卢女士"
        cn_female = ('女士', '小姐', '夫人', '太太')
        cn_male = ('先生',)
        for honorific in cn_female:
            if name_stripped.endswith(honorific):
                return "female"
        for honorific in cn_male:
            if name_stripped.endswith(honorific):
                return "male"

        # 英文敬称是前缀：如 "Ms. Li"
        en_female = ('Ms.', 'Mrs.', 'Miss', 'ms.', 'mrs.', 'miss')
        en_male = ('Mr.', 'mr.')
        for honorific in en_female:
            if name_stripped.startswith(honorific):
                return "female"
        for honorific in en_male:
            if name_stripped.startswith(honorific):
                return "male"

        # ── 策略2：去掉敬称，字符集推断 ──
        clean_name = name_stripped
        for suffix in ('女士', '小姐', '夫人', '太太', '先生'):
            if clean_name.endswith(suffix):
                clean_name = clean_name[:-len(suffix)]
                break

        if len(clean_name) < 2:
            return "male"

        given_name = clean_name[1:]  # 去掉姓
        if not given_name:
            return "male"

        female_count = sum(1 for ch in given_name if ch in _FEMALE_NAME_CHARS)
        male_count = sum(1 for ch in given_name if ch in _MALE_NAME_CHARS)

        if female_count > male_count:
            return "female"
        elif male_count > female_count:
            return "male"

        # ── 策略3：默认 ──
        return "male"
    
    @staticmethod
    def _chinese_name_to_pinyin(name: str) -> str:
        """
        将中文姓名转换为拼音形式（取姓氏拼音）
        
        Args:
            name: 中文姓名
            
        Returns:
            姓氏拼音（如 "Zhang"）
        """
        pinyin_map = {
            '张': 'Zhang', '李': 'Li', '王': 'Wang', '刘': 'Liu', '陈': 'Chen',
            '杨': 'Yang', '黄': 'Huang', '赵': 'Zhao', '周': 'Zhou', '吴': 'Wu',
            '徐': 'Xu', '孙': 'Sun', '马': 'Ma', '朱': 'Zhu', '胡': 'Hu',
            '郭': 'Guo', '何': 'He', '林': 'Lin', '罗': 'Luo', '高': 'Gao',
            '郑': 'Zheng', '梁': 'Liang', '谢': 'Xie', '宋': 'Song', '唐': 'Tang',
            '许': 'Xu', '韩': 'Han', '冯': 'Feng', '邓': 'Deng', '曹': 'Cao',
            '彭': 'Peng', '曾': 'Zeng', '萧': 'Xiao', '田': 'Tian', '董': 'Dong',
            '袁': 'Yuan', '潘': 'Pan', '于': 'Yu', '蒋': 'Jiang', '蔡': 'Cai',
            '余': 'Yu', '杜': 'Du', '叶': 'Ye', '程': 'Cheng', '苏': 'Su',
            '魏': 'Wei', '吕': 'Lv', '丁': 'Ding', '任': 'Ren', '沈': 'Shen',
            '姚': 'Yao', '卢': 'Lu', '姜': 'Jiang', '崔': 'Cui', '钟': 'Zhong',
            '谭': 'Tan', '陆': 'Lu', '汪': 'Wang', '范': 'Fan', '金': 'Jin',
            '石': 'Shi', '廖': 'Liao', '贾': 'Jia', '夏': 'Xia', '韦': 'Wei',
            '付': 'Fu', '方': 'Fang', '白': 'Bai', '邹': 'Zou', '孟': 'Meng',
            '熊': 'Xiong', '秦': 'Qin', '邱': 'Qiu', '江': 'Jiang', '尹': 'Yin',
            '薛': 'Xue', '闫': 'Yan', '段': 'Duan', '雷': 'Lei', '黎': 'Li',
            '史': 'Shi', '龙': 'Long', '贺': 'He', '顾': 'Gu', '毛': 'Mao',
            '郝': 'Hao', '龚': 'Gong', '邵': 'Shao', '万': 'Wan', '钱': 'Qian',
            '严': 'Yan', '覃': 'Qin', '武': 'Wu', '戚': 'Qi', '阚': 'Kan',
            '雍': 'Yong',
        }
        
        if not name or len(name) < 1:
            return "Candidate"

        # In ``Charles Yang (杨超)``, the parenthesized Chinese name is
        # authoritative for surname inference.
        bilingual_cn = re.search(r'[（(]\s*([\u3400-\u9fff]{2,})\s*[）)]', str(name))
        if bilingual_cn:
            name = bilingual_cn.group(1)
        
        first_char = name[0]
        # 首字符不是中文 → 输入已是拼音/英文（如 "Zhang Wei"、"Mr. Zhao"），
        # 提取首个英文单词作为姓氏，避免返回 "Candidate"
        if not ('\u4e00' <= first_char <= '\u9fff'):
            m = re.match(r'[A-Za-z]+', name.strip())
            return m.group(0) if m else "Candidate"
        return pinyin_map.get(first_char) or lazy_pinyin(first_char)[0].capitalize()
    
    @staticmethod
    def anonymize_resume(resume_data: ResumeData) -> ResumeData:
        """
        对简历数据进行脱敏处理（Pipeline步骤3的一部分）
        
        Args:
            resume_data: 原始简历数据
            
        Returns:
            脱敏后的简历数据
            
        脱敏规则：
        - 姓名 → Mr./Ms. + 姓氏拼音（英文模板）或 姓+先生/女士（中文模板）
        - 性别自动从姓名中的常用字推断
        - 移除电话、邮箱、年龄、出生日期、所在地
        - 保留公司名（不再映射为 Company A/B/C）
        - 保留：工作经历、技能、学历背景
        """
        try:
            anonymized = resume_data.model_copy(deep=True)
            
            # ── 1. 性别推断 ──
            gender = resume_data.gender
            if not gender and anonymized.name:
                gender = AnonymizerService._infer_gender(anonymized.name)
            if not gender:
                gender = "male"  # 默认
            anonymized.gender = gender
            
            # ── 2. 姓名脱敏 ──
            if anonymized.name:
                name_pinyin = AnonymizerService._chinese_name_to_pinyin(anonymized.name)
                bilingual_cn = re.search(
                    r'[（(]\s*([\u3400-\u9fff]{2,})\s*[）)]',
                    str(anonymized.name),
                )
                source_cn = bilingual_cn.group(1) if bilingual_cn else str(anonymized.name)
                surname_cn = source_cn[0] if source_cn else ""
                if not ('\u4e00' <= surname_cn <= '\u9fff'):
                    surname_cn = {
                        'fang': '方', 'peng': '彭', 'kan': '阚', 'guo': '郭',
                        'zhao': '赵', 'zhang': '张', 'li': '李', 'wang': '王',
                        'chen': '陈', 'he': '何', 'yang': '杨', 'liu': '刘',
                    }.get(name_pinyin.lower(), surname_cn)
                
                # 根据模板语言选择称呼格式
                lang = getattr(anonymized, 'language', 'CN') or 'CN'
                
                if lang == 'CN':
                    # 中文模板：张先生 / 李女士
                    if gender == 'female':
                        anonymized.name = f"{surname_cn}女士"
                    else:
                        anonymized.name = f"{surname_cn}先生"
                    anonymized.anonymized_name = anonymized.name
                else:
                    # 英文模板：Mr. Zhang / Ms. Li
                    if gender == 'female':
                        anonymized.name = f"Ms. {name_pinyin}"
                    else:
                        anonymized.name = f"Mr. {name_pinyin}"
                    anonymized.anonymized_name = anonymized.name

                # ── 始终保存中文敬称格式，用于文件命名 ──
                if gender == 'female':
                    anonymized.anonymized_name_cn = f"{surname_cn}女士"
                else:
                    anonymized.anonymized_name_cn = f"{surname_cn}先生"
            
            # ── 3. 移除敏感信息 ──
            anonymized.phone = None
            anonymized.email = None
            anonymized.age = None
            anonymized.birth_date = None
            anonymized.location = None
            
            # ── 4. 保留公司名（不再映射）──
            # 公司名保持原样，不再替换为 Company A/B/C
            
            # 标记为已脱敏
            anonymized.is_anonymized = True
            
            return anonymized
            
        except Exception as e:
            error_detail = f"简历脱敏失败: {str(e)}"
            print(f"[Anonymizer Error] {error_detail}\n{traceback.format_exc()}")
            raise HTTPException(status_code=500, detail=error_detail)

