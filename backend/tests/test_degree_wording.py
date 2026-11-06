import pytest
from app.schemas.education import normalize_degree


@pytest.mark.parametrize('source, expected', [
    ('本科', '学士'), ('大学本科学历', '学士'),
    ('硕士研究生', '硕士'), ('博士研究生（在读）', '博士（在读）'),
    ('工学硕士', '工学硕士'), ('本科/学士', '学士'),
    ('研究生', '学位未注明'), ('专科', '专科'),
    ('Bachelor of Science', 'Bachelor of Science'), (None, None),
])
def test_degree_wording(source, expected):
    assert normalize_degree(source) == expected
