"""Validated desktop job envelopes and durable, exclusive operation ownership."""

from copy import deepcopy
from datetime import datetime
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
from uuid import uuid4

OPERATIONS = {'collect_outlook', 'proof_idml', 'proof_docx', 'export_final_idml'}


def confined_path(value, root):
    path = Path(value)
    if not path.is_absolute() or '..' in path.parts:
        raise ValueError('Job paths must be absolute without traversal')
    for ancestor in (path, *path.parents):
        if ancestor.exists() and (ancestor.is_symlink() or
                getattr(ancestor.lstat(), 'st_file_attributes', 0) & stat.FILE_ATTRIBUTE_REPARSE_POINT):
            raise ValueError('Reparse paths are not allowed')
    resolved = path.resolve()
    if not resolved.is_relative_to(Path(root).resolve()) or resolved == Path(root).resolve():
        raise ValueError('Job path outside approved root')
    return resolved


def validate_job(request, approved_root, now):
    job = deepcopy(request)
    if job.get('operation') not in OPERATIONS:
        raise ValueError('Unsupported desktop operation')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}', job.get('id', '')):
        raise ValueError('Invalid job id')
    deadline = datetime.fromisoformat(job['deadline'])
    if deadline.tzinfo is None or now.tzinfo is None or deadline <= now:
        raise ValueError('Expired or unzoned deadline')
    paths = [confined_path(job[key], approved_root) for key in ('input', 'output', 'result')]
    if len(set(paths)) != 3:
        raise ValueError('Input, output and result must be distinct')
    if any(path.name in {'desktop.lock', 'desktop-stage.json'} for path in paths):
        raise ValueError('Reserved desktop state path')
    if not re.fullmatch('[0-9a-f]{64}', job.get('input_hash', '')):
        raise ValueError('Invalid input hash')
    if sha256(paths[0].read_bytes()).hexdigest() != job['input_hash']:
        raise ValueError('Job input hash mismatch')
    if paths[1].exists() or paths[2].exists():
        raise ValueError('Job destinations already exist')
    return job


def accept_result(request, result):
    for key in ('id', 'operation', 'input_hash'):
        if result.get(key) != request.get(key) or key not in result:
            raise ValueError('Mismatched job result '+key)
    if result.get('status') not in {'complete', 'pending', 'failed'}:
        raise ValueError('Unknown result status')
    if result['status'] == 'complete':
        try:
            actual = sha256(Path(request['output']).read_bytes()).hexdigest()
        except OSError as exc:
            raise ValueError('Completed job output unavailable') from exc
        if actual != result.get('output_hash'):
            raise ValueError('Completed job output hash mismatch')
    return deepcopy(result)


def atomic_record(path, value):
    path = Path(path)
    temporary = path.with_name(path.name+'.'+uuid4().hex+'.tmp')
    with temporary.open('x', encoding='utf-8') as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def run_job(request, approved_root, launch, now, sleep):
    """Bound the caller's wait, never terminate a desktop process on timeout.

    `launch` is a trusted fixed-operation dispatcher, never a request-supplied command.
    Uncertain completion retains ownership for explicit reconciliation.
    """
    root = Path(approved_root).resolve()
    root.mkdir(parents=True, exist_ok=True)
    lock = root/'desktop.lock'
    with lock.open('x', encoding='utf-8') as stream:
        json.dump({'id': request.get('id'), 'owner_pid': os.getpid()}, stream)
    launched = False
    verified = False
    stage = root/'desktop-stage.json'
    try:
        job = validate_job(request, root, now())
        atomic_record(stage, {'id': job['id'], 'stage': 'launching'})
        # A launch exception may occur after process creation; retain the lock.
        launched = True
        process = launch(job)
        atomic_record(stage, {'id': job['id'], 'stage': 'running', 'pid': process.pid})
        while process.poll() is None:
            if now() >= datetime.fromisoformat(job['deadline']):
                atomic_record(stage, {'id': job['id'], 'stage': 'ownership_unresolved', 'pid': process.pid})
                return {**{k: job[k] for k in ('id', 'operation', 'input_hash')},
                        'status': 'pending', 'reason': 'operation_may_still_be_active'}
            sleep(0.25)
        if process.poll() != 0:
            raise RuntimeError('Desktop worker failed; ownership requires reconciliation')
        result = accept_result(job, json.loads(Path(job['result']).read_text(encoding='utf-8-sig')))
        if result['status'] == 'failed':
            raise RuntimeError('Desktop operation failed; ownership requires reconciliation')
        atomic_record(stage, {'id': job['id'], 'stage': result['status'], 'pid': process.pid})
        verified = True
        return result
    finally:
        if not launched or verified:
            lock.unlink()
