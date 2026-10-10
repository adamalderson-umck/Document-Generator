"""Single on-demand dispatch entry point; no recurring timer."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

from .jobs import accept_result, confined_path, run_job, validate_job, atomic_record
from .native import launch_desktop_job, worker_launch_paths


def queue_job(request, root):
    root = Path(root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root/'submission.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(request['id'])
    try:
        if (root/'desktop.lock').exists():
            raise FileExistsError('Desktop ownership remains active or unresolved')
        dispatch = root/'dispatch.json'
        if dispatch.exists():
            previous = json.loads(dispatch.read_text(encoding='utf-8'))
            result_path = confined_path(previous['result'], root)
            if not result_path.exists():
                raise FileExistsError('Previous dispatch has not completed')
            result = accept_result(previous, json.loads(result_path.read_text(encoding='utf-8-sig')))
            if result['status'] == 'failed':
                raise FileExistsError('Failed dispatch requires reconciliation')
        validate_job(request, root, datetime.now(timezone.utc))
        reserved = worker_launch_paths(request['id'], root)
        job_paths = {Path(request[key]).resolve() for key in ('input', 'output', 'result')}
        for path in reserved:
            if path in job_paths:
                raise ValueError(f'Worker-owned path cannot be a job input/output/result: {path.name}')
            if path.exists() or path.is_symlink():
                raise FileExistsError(f'Worker-owned launch file already exists: {path.name}')
        atomic_record(dispatch, request)
    finally:
        lock.unlink()


def run_queued_job(root, runner=None):
    root = Path(root).resolve()
    request = json.loads((root/'dispatch.json').read_text(encoding='utf-8'))
    for key in ('input', 'output', 'result'):
        confined_path(request[key], root)
    if sha256(Path(request['input']).read_bytes()).hexdigest() != request['input_hash']:
        raise ValueError('Dispatch input changed')
    if Path(request['result']).exists():
        return accept_result(request, json.loads(Path(request['result']).read_text(encoding='utf-8-sig')))
    if runner is not None:
        return runner(request, root)
    return run_job(request, root, lambda job: launch_desktop_job(job, root),
                   lambda: datetime.now(timezone.utc), time.sleep)


if __name__ == '__main__':
    print(json.dumps(run_queued_job(sys.argv[1])))
