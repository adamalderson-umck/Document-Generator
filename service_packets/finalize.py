"""Capture explicitly designated finals; promote only validated main bulletins."""

from datetime import date, datetime, timedelta, timezone
from hashlib import sha256
import json
import os
from pathlib import Path
from uuid import uuid4
import xml.etree.ElementTree as ET
from zipfile import ZipFile

from .idml import inspect_baseline
from .model import ROLES
from .jobs import accept_result


def finalize_worker_export(root, designation, request, result):
    """Validate a registered INDD export before promoting its captured IDML."""
    if request.get('operation') != 'export_final_idml':
        raise ValueError('Expected final-IDML export operation')
    accepted = accept_result(request, result)
    if accepted['status'] != 'complete':
        return {'status': accepted['status'], 'reason': accepted.get('reason', 'export_incomplete'), 'promoted': False}
    native = accepted.get('native', {})
    if (native.get('id') != request['id'] or native.get('input_hash') != request['input_hash']
            or native.get('proof_status') != 'visual_review_pending'
            or native.get('output_hash') != accepted['output_hash']
            or native.get('bad_fonts') != 0 or native.get('bad_links') != 0):
        raise ValueError('Unverified native export or unavailable resources')
    original = Path(designation['path']).resolve()
    if original.suffix.lower() != '.indd' or sha256(original.read_bytes()).hexdigest() != request['input_hash']:
        raise ValueError('Designated INDD differs from exported snapshot')
    capture = dict(designation, path=request['output'], original_source={
        'path': str(original), 'sha256': request['input_hash'], 'job_id': request['id'],
        'native_export': native})
    return finalize_packet(root, capture)


def finalize_packet(root, designation, adapter=None):
    state = Path(root)/'state/service_packets'
    state.mkdir(parents=True, exist_ok=True)
    lock = state/'finalize.lock'
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    try:
        return _capture(root, designation, adapter)
    finally:
        lock.unlink()


def _capture(root, designation, adapter):
    if not str(designation.get('user_designation', '')).strip():
        raise ValueError('Explicit user designation is required')
    day = date.fromisoformat(designation['date'])
    if day.weekday() != 6:
        raise ValueError('Final service date must be Sunday')
    service = designation['service']
    if service not in ROLES:
        raise ValueError('Unknown service')
    source = Path(designation['path']).resolve()
    suffix = source.suffix.lower()
    if suffix not in {'.idml', '.indd'}:
        raise ValueError('Final bulletin must be IDML or INDD')
    if suffix == '.indd' and adapter is None:
        return {'status': 'pending', 'reason': 'saved_idml_required', 'promoted': False}
    state = Path(root)/'state/service_packets'
    state.mkdir(parents=True, exist_ok=True)
    pointer = state/'baseline.json'
    if service == 'main' and pointer.exists():
        previous = json.loads(pointer.read_text(encoding='utf-8'))
        if str(day) < previous['date'] and not designation.get('exception_evidence'):
            raise ValueError('Older final requires explicit exception evidence')
    capture = state/'finals'/str(day)/service/uuid4().hex
    capture.mkdir(parents=True)
    content = source.read_bytes()
    target = capture/'bulletin.idml'
    native = None
    if suffix == '.indd':
        scratch = capture/'source.indd'
        scratch.write_bytes(content)
        request = {'id': uuid4().hex, 'format': 'indd', 'input': str(scratch.resolve()),
                   'output': str(target.resolve()), 'result': str((capture/'export-result.json').resolve()),
                   'sha256': sha256(content).hexdigest(),
                   'deadline': (datetime.now(timezone.utc)+timedelta(minutes=15)).isoformat()}
        native = adapter(request)
        if native.get('id') != request['id'] or native.get('input_hash') != request['sha256']:
            raise ValueError('Stale or mismatched native export result')
        if native.get('proof_status') == 'pending':
            return {'status': 'pending', 'reason': native.get('reason', 'native_export_pending'), 'promoted': False}
        if native.get('proof_status') != 'visual_review_pending':
            raise ValueError('Native export did not complete')
        if native.get('bad_fonts') != 0 or native.get('bad_links') != 0:
            raise ValueError('Final native export has unavailable fonts or links')
        if native.get('output_hash') != sha256(target.read_bytes()).hexdigest():
            raise ValueError('Native export output hash mismatch')
    else:
        with target.open('xb') as stream:
            stream.write(content)
    info = inspect_baseline(target)
    with ZipFile(target) as archive:
        for name in info['stories'].values():
            story = ET.fromstring(archive.read(name))
            if not ''.join(node.text or '' for node in story.iter('Content')).strip():
                raise ValueError('Final labeled story is empty')
            for paragraph in story.iter('ParagraphStyleRange'):
                if paragraph.get('AppliedParagraphStyle') not in info['styles']:
                    raise ValueError('Final story refers to an undefined paragraph style')
    baseline = {'path': str(target.resolve()), 'sha256': info['sha256'],
                'date': str(day), 'service': service, 'finalized': True,
                'source_path': str(source), 'user_designation': designation['user_designation']}
    if designation.get('exception_evidence'):
        baseline['exception_evidence'] = designation['exception_evidence']
    if designation.get('original_source'):
        baseline['original_source'] = designation['original_source']
    record = {'status': 'captured', 'baseline': baseline, 'promoted': service == 'main',
              'outstanding': ['cameras', 'sound'] if service == 'main' else [],
              'technical': {}}
    if native is not None:
        record['native_export'] = native
    if service == 'main':
        from docx import Document
        for kind in ('cameras', 'sound'):
            supplied = designation.get('technical', {}).get(kind)
            if not supplied:
                continue
            technical_source = Path(supplied).resolve()
            technical_bytes = technical_source.read_bytes()
            technical_target = capture/(kind+'.docx')
            with technical_target.open('xb') as stream:
                stream.write(technical_bytes)
            Document(technical_target)  # Validate the captured package before promotion.
            record['technical'][kind] = {'path': str(technical_target.resolve()),
                                         'sha256': sha256(technical_bytes).hexdigest(),
                                         'source_path': str(technical_source)}
            record['outstanding'].remove(kind)
    # The immutable capture records intent, not successful pointer replacement.
    # Only baseline.json establishes which capture was actually promoted.
    capture_record = {key: value for key, value in record.items() if key != 'promoted'}
    capture_record['promotion_requested'] = service == 'main'
    (capture/'record.json').write_text(json.dumps(capture_record, indent=2), encoding='utf-8')
    if service == 'main':
        temporary = state/('baseline-'+uuid4().hex+'.tmp')
        with temporary.open('x', encoding='utf-8') as stream:
            json.dump(baseline, stream, indent=2)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, state/'baseline.json')
    return record
