"""
PPT模板配置
定义模板文件和字段映射关系
"""
from enum import Enum


class TemplateType(str, Enum):
    """模板类型枚举"""
    ONEPAGER_CN = "onepager_cn"
    ONEPAGER_EN = "onepager_en"
    NEW_CN = "new_cn"
    NEW_EN = "new_en"


class Orientation(str, Enum):
    """模板方向枚举"""
    VERTICAL = "vertical"
    HORIZONTAL = "horizontal"


# 根据方向获取默认模板ID的映射
ORIENTATION_TO_TEMPLATE = {
    "CN": {
        Orientation.VERTICAL: TemplateType.NEW_CN,
        Orientation.HORIZONTAL: TemplateType.ONEPAGER_CN
    },
    "EN": {
        Orientation.VERTICAL: TemplateType.NEW_EN,
        Orientation.HORIZONTAL: TemplateType.ONEPAGER_EN
    }
}


TEMPLATE_CONFIG = {
    "onepager_cn": {
        "file": "Onepager_Template_CN.pptx",
        "orientation": "landscape",
        "language": "CN"
    },
    "onepager_en": {
        "file": "Onepager_Template_EN.pptx",
        "orientation": "landscape",
        "language": "EN"
    },
    "new_cn": {
        "file": "New_Template_IAV_Resume_CN.pptx",
        "orientation": "portrait",
        "language": "CN"
    },
    "new_en": {
        "file": "New_Template_IAV_Resume_EN.pptx",
        "orientation": "portrait",
        "language": "EN"
    }
}

# 基础模板字段映射（模板字段名 -> 数据路径，不带索引）
FIELD_MAPPING = {
    "{{name}}": "name",
    "{{technical_area}}": "technical_area",
    "{{total_exp}}": "total_exp",
    "{{position}}": "position",
    "{{tech_skills}}": "tech_skills",
    "{{lang_skills}}": "lang_skills",
    "{{lang_skills_level}}": "lang_skills_level",
    "{{training_exp}}": "training_exp"
}

# 工作经历字段映射模板
WORK_FIELDS = {
    "company": "work[{index}].company",
    "period": "work[{index}].period",
    "role": "work[{index}].role",
    "tasks": "work[{index}].tasks"
}

# 项目经历字段映射模板
PROJECT_FIELDS = {
    "company": "project[{index}].company",
    "period": "project[{index}].period",
    "name": "project[{index}].name",
    "role": "project[{index}].role",
    "tasks": "project[{index}].tasks"
}

# 教育经历字段映射模板
EDUCATION_FIELDS = {
    "period": "education[{index}].period",
    "school": "education[{index}].school",
    "degree": "education[{index}].degree",
    "major": "education[{index}].major"
}

# 数组类型配置
ARRAY_FIELDS = {
    "work": {
        "template": WORK_FIELDS,
        "placeholder_prefix": "work.",
        "data_key": "work"
    },
    "project": {
        "template": PROJECT_FIELDS,
        "placeholder_prefix": "project.",
        "data_key": "project"
    },
    "education": {
        "template": EDUCATION_FIELDS,
        "placeholder_prefix": "education.",
        "data_key": "education"
    }
}
