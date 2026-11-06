"""Thread-safe, single-use confirmation for one CV task."""
from threading import Lock

from app.services.gender_service import detect_source_gender


class GenderConfirmation:
    def __init__(self):
        self._lock = Lock()
        self.gender = None
        self.waiting = False
        self.extracted = None

    def inspect(self, source_text, extracted):
        with self._lock:
            if self.extracted is None:
                self.extracted = extracted.model_dump()
                self.gender = detect_source_gender(source_text)
            self.waiting = self.gender is None
            return self.gender

    def confirm(self, gender):
        with self._lock:
            if gender not in ('male', 'female'):
                raise ValueError('Invalid gender')
            if not self.waiting or self.extracted is None:
                raise ValueError('Task is not waiting for gender')
            self.gender = gender
            self.waiting = False

    @property
    def required_input(self):
        if not self.waiting:
            return None
        return {'field': 'gender', 'reason': 'missing_or_ambiguous_source_gender'}
