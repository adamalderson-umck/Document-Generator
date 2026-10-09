import pytest
from service_packets.proof import proof_artifact


def test_busy_application_never_composes():
    class Busy:
        def has_user_documents(self):
            return True
        def compose(self, request):
            raise AssertionError('Must not open scratch document')
    assert proof_artifact({'id': 'p1'}, Busy())['proof_status'] == 'pending'


def test_composition_failure_is_not_success():
    class Failed:
        def has_user_documents(self):
            return False
        def compose(self, request):
            raise RuntimeError('Export failed')
    result = proof_artifact({'id': 'p1'}, Failed())
    assert result['proof_status'] == 'failed'
    assert 'Export failed' in result['error']


def test_export_requires_separate_visual_review():
    class Available:
        def has_user_documents(self):
            return False
        def compose(self, request):
            return {'id': request['id'], 'pages': 4, 'layout_findings': []}
    result = proof_artifact({'id': 'p1'}, Available())
    assert result['proof_status'] == 'visual_review_pending'


def test_stale_result_rejected():
    class Stale:
        def has_user_documents(self):
            return False
        def compose(self, request):
            return {'id': 'old'}
    assert proof_artifact({'id': 'p1'}, Stale())['proof_status'] == 'failed'
