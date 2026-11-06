from pathlib import Path

import pytest

from app.core.cv_rules import CVRules
from app.prompts import load_cv_extraction_prompt


@pytest.mark.parametrize('kwargs', [
    {'extraction_max_input_chars': 0},
    {'translation_max_attempts': -1},
    {'body_font_size_pt': 0},
    {'module_spacing_cm': -0.1},
    {'ambiguous_degree_label': ' '},
])
def test_invalid_policy_values_are_rejected(kwargs):
    with pytest.raises(ValueError):
        CVRules(**kwargs)


def test_prompt_loading_does_not_depend_on_working_directory(tmp_path, monkeypatch):
    expected = load_cv_extraction_prompt()
    monkeypatch.chdir(tmp_path)
    assert load_cv_extraction_prompt() == expected
    assert '不得遗漏任何职责' in expected
    assert 'If an education section is present' in expected


def test_prompt_is_read_for_each_call(tmp_path, monkeypatch):
    import app.prompts as prompts
    monkeypatch.setattr(prompts, '__file__', str(tmp_path / '__init__.py'))
    prompt_file = Path(tmp_path / 'cv_extraction.txt')
    prompt_file.write_text('first', encoding='utf-8')
    assert load_cv_extraction_prompt() == 'first'
    prompt_file.write_text('updated', encoding='utf-8')
    assert load_cv_extraction_prompt() == 'updated'
