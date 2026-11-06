from concurrent.futures import ThreadPoolExecutor

import pytest

from app.schemas.resume import ResumeData
from app.services.cv_gender_confirmation import GenderConfirmation


def test_explicit_source_overrides_model_guess():
    state = GenderConfirmation()
    assert state.inspect('Gender: Female', ResumeData(gender='male')) == 'female'
    assert state.required_input is None
    with pytest.raises(ValueError):
        state.confirm('male')


def test_unknown_gender_requires_confirmation_and_keeps_extraction():
    state = GenderConfirmation()
    assert state.inspect('Software engineer', ResumeData(name='Alex', gender='male')) is None
    assert state.required_input['field'] == 'gender'
    with pytest.raises(ValueError):
        state.confirm('invalid')
    assert state.waiting
    state.confirm('female')
    assert state.inspect('', ResumeData()) == 'female'
    assert state.extracted['name'] == 'Alex'
    assert state.required_input is None


def test_concurrent_confirmation_is_accepted_only_once():
    state = GenderConfirmation()
    state.inspect('', ResumeData())

    def submit(gender):
        try:
            state.confirm(gender)
            return True
        except ValueError:
            return False

    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sum(pool.map(submit, ['female', 'male'])) == 1


def test_confirmation_before_extraction_is_rejected():
    with pytest.raises(ValueError):
        GenderConfirmation().confirm('female')
