"""Single on-demand dispatch entry point; no recurring timer."""

from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

from .jobs import accept_result, confined_path, run_job
from .native import launch_desktop_job


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
