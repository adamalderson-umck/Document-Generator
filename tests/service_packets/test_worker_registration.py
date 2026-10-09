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
