from datetime import datetime, timedelta, timezone
from hashlib import sha256
import json

from service_packets.scheduled import run_queued_job, queue_job
import pytest


def test_completed_dispatch_is_not_launched_twice(tmp_path):
    source = tmp_path/'input.docx'; source.write_bytes(b'input')
    output = tmp_path/'proof.pdf'; output.write_bytes(b'proof')
    request = {'id':'one','operation':'proof_docx','input':str(source),
               'input_hash':sha256(b'input').hexdigest(),'output':str(output),
               'result':str(tmp_path/'result.json'),
               'deadline':(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()}
    result = {**{k:request[k] for k in ('id','operation','input_hash')},
              'status':'complete','output_hash':sha256(b'proof').hexdigest()}
    (tmp_path/'dispatch.json').write_text(json.dumps(request))
    (tmp_path/'result.json').write_text(json.dumps(result))
    def forbidden(*args): raise AssertionError('Must not launch completed dispatch')
    assert run_queued_job(tmp_path, forbidden) == result


def test_submission_cannot_replace_unfinished_dispatch(tmp_path):
    source = tmp_path/'input.idml';source.write_bytes(b'input')
    request = {'id':'first','operation':'proof_idml','input':str(source),
               'input_hash':sha256(b'input').hexdigest(),'output':str(tmp_path/'out.pdf'),
               'result':str(tmp_path/'result.json'),
               'deadline':(datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()}
    queue_job(request,tmp_path)
    before=(tmp_path/'dispatch.json').read_bytes()
    with pytest.raises(FileExistsError):
        queue_job(dict(request,id='second'),tmp_path)
    assert (tmp_path/'dispatch.json').read_bytes()==before


@pytest.mark.parametrize('suffix', ['-request.json', '.log'])
@pytest.mark.parametrize('previous_dispatch', [False, True])
def test_submission_rejects_worker_file_collision_without_changing_ownership(
        tmp_path, suffix, previous_dispatch):
    source = tmp_path/'input.idml'
    source.write_bytes(b'input')
    request = {'id': 'next', 'operation': 'proof_idml', 'input': str(source),
               'input_hash': sha256(source.read_bytes()).hexdigest(),
               'output': str(tmp_path/'next.pdf'), 'result': str(tmp_path/'next-result.json'),
               'deadline': (datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()}
    dispatch = tmp_path/'dispatch.json'
    if previous_dispatch:
        previous = dict(request, id='previous', output=str(tmp_path/'previous.pdf'),
                        result=str(tmp_path/'previous-result.json'))
        previous_result = {key: previous[key] for key in ('id', 'operation', 'input_hash')}
        previous_result.update(status='pending', reason='user_documents_open')
        dispatch.write_text(json.dumps(previous))
        (tmp_path/'previous-result.json').write_text(json.dumps(previous_result))
    before = dispatch.read_bytes() if dispatch.exists() else None
    reserved = tmp_path/('next'+suffix)
    reserved.write_bytes(b'Existing worker-owned evidence')
    with pytest.raises(FileExistsError, match='Worker-owned'):
        queue_job(request, tmp_path)
    assert (dispatch.read_bytes() if dispatch.exists() else None) == before
    assert reserved.read_bytes() == b'Existing worker-owned evidence'
    assert not (tmp_path/'desktop.lock').exists()
    assert not (tmp_path/'desktop-stage.json').exists()
    assert not (tmp_path/'submission.lock').exists()


@pytest.mark.parametrize('field', ['output', 'result'])
@pytest.mark.parametrize('suffix', ['-request.json', '.log'])
def test_submission_cannot_assign_worker_owned_path_to_job_output(tmp_path, field, suffix):
    source = tmp_path/'input.idml'
    source.write_bytes(b'input')
    request = {'id': 'next', 'operation': 'proof_idml', 'input': str(source),
               'input_hash': sha256(source.read_bytes()).hexdigest(),
               'output': str(tmp_path/'next.pdf'), 'result': str(tmp_path/'next-result.json'),
               'deadline': (datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()}
    request[field] = str(tmp_path/('next'+suffix))
    with pytest.raises(ValueError, match='Worker-owned'):
        queue_job(request, tmp_path)
    assert not (tmp_path/'dispatch.json').exists()
    assert not (tmp_path/'desktop.lock').exists()
    assert not (tmp_path/'submission.lock').exists()


def test_successful_submission_leaves_worker_files_for_launcher(tmp_path):
    from service_packets.native import worker_launch_paths
    source = tmp_path/'input.idml'
    source.write_bytes(b'input')
    request = {'id': 'next', 'operation': 'proof_idml', 'input': str(source),
               'input_hash': sha256(source.read_bytes()).hexdigest(),
               'output': str(tmp_path/'next.pdf'), 'result': str(tmp_path/'next-result.json'),
               'deadline': (datetime.now(timezone.utc)+timedelta(minutes=2)).isoformat()}
    queue_job(request, tmp_path)
    assert json.loads((tmp_path/'dispatch.json').read_text()) == request
    assert all(not path.exists() for path in worker_launch_paths(request['id'], tmp_path))
    assert not (tmp_path/'desktop.lock').exists()
    assert not (tmp_path/'submission.lock').exists()
