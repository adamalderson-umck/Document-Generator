from datetime import datetime, timedelta, timezone
from hashlib import sha256
import pytest

from service_packets.jobs import accept_result, validate_job, run_job, atomic_record


def request(tmp_path):
    source = tmp_path/'input.idml'
    source.write_bytes(b'snapshot')
    return {'id': 'job-1', 'operation': 'proof_idml', 'input': str(source),
            'input_hash': sha256(source.read_bytes()).hexdigest(),
            'output': str(tmp_path/'proof.pdf'), 'result': str(tmp_path/'result.json'),
            'deadline': (datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()}


def test_old_success_cannot_satisfy_new_request():
    with pytest.raises(ValueError):
        accept_result({'id': 'new', 'operation': 'proof_idml', 'input_hash': 'a'*64},
                      {'id': 'old', 'operation': 'proof_idml', 'input_hash': 'a'*64, 'status': 'complete'})


@pytest.mark.parametrize('problem', ['operation', 'escape', 'expired', 'hash'])
def test_invalid_job_is_rejected_before_dispatch(tmp_path, problem):
    job = request(tmp_path)
    if problem == 'operation': job['operation'] = 'arbitrary_command'
    if problem == 'escape': job['output'] = str(tmp_path.parent/'escape.pdf')
    if problem == 'expired': job['deadline'] = '2020-01-01T00:00:00+00:00'
    if problem == 'hash': job['input_hash'] = '0'*64
    with pytest.raises(ValueError):
        validate_job(job, tmp_path, datetime.now(timezone.utc))


def test_complete_result_requires_matching_output_bytes(tmp_path):
    job = request(tmp_path)
    validate_job(job, tmp_path, datetime.now(timezone.utc))
    result = {**{key: job[key] for key in ('id', 'operation', 'input_hash')},
              'status': 'complete', 'output_hash': '0'*64}
    with pytest.raises(ValueError):
        accept_result(job, result)


def test_timed_out_job_keeps_ownership_and_cannot_reenter(tmp_path):
    job = request(tmp_path)
    clock = [datetime.now(timezone.utc)]
    class Active:
        pid = 123
        def poll(self): return None
    def advance(seconds): clock[0] += timedelta(minutes=5)
    result = run_job(job, tmp_path, lambda job: Active(), lambda: clock[0], advance)
    assert result['status'] == 'pending'
    assert result['reason'] == 'operation_may_still_be_active'
    with pytest.raises(FileExistsError):
        run_job(job, tmp_path, lambda job: pytest.fail('Must not launch again'), lambda: clock[0], advance)


def test_completed_job_releases_ownership_only_after_result_validation(tmp_path):
    from pathlib import Path
    job = request(tmp_path)
    class Finished:
        pid = 123
        def poll(self): return 0
    def launch(job):
        Path(job['output']).write_bytes(b'proof')
        atomic_record(job['result'], {**{k: job[k] for k in ('id','operation','input_hash')},
                      'status':'complete','output_hash':sha256(b'proof').hexdigest()})
        return Finished()
    result = run_job(job, tmp_path, launch, lambda: datetime.now(timezone.utc), lambda s: None)
    assert result['status'] == 'complete'
    assert not (tmp_path/'desktop.lock').exists()
