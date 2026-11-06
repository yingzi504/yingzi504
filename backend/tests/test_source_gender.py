import pytest

from app.services.gender_service import detect_source_gender


@pytest.mark.parametrize('source, expected', [
    ('姓名：王伟\n性别：女\n工作经历', 'female'),
    ('Gender:\nFemale', 'female'),
    ('Sex: M', 'male'),
    ('王芳 | 男 | 30岁', 'male'),
    ('王芳\n软件工程师', None),
    ('Developed software for female customers', None),
    ('Gender: female\n性别：男', None),
    ('', None),
])
def test_only_explicit_unambiguous_source_gender(source, expected):
    assert detect_source_gender(source) == expected
