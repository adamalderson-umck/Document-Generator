"""Publish a new editable draft revision without touching prior handoffs."""

from datetime import date, timedelta
from hashlib import sha256
import json
from pathlib import Path

from .idml import render_idml
from .model import validate_packet
from .technical import render_technical


def build_packet(packet, root, layout, cues, templates):
    packet = validate_packet(packet)
    parent = Path(root)/'outputs'/packet['date']
    parent.mkdir(parents=True, exist_ok=True)
    for number in range(1, 10000):
        directory = parent/f'rev-{number:03d}'
        try:
            directory.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise RuntimeError('Revision allocation exhausted')
    result = {'date': packet['date'], 'revision': directory.name, 'artifacts': [],
              'issues': packet['issues'], 'review_path': str(directory/'review.md')}
    baseline = packet.get('baseline')
    frozen = None
    if not baseline:
        result['issues'].append({'code': 'baseline_missing', 'message': 'Bulletins unavailable; supply eligible finalized main baseline.'})
    else:
        try:
            if baseline.get('service') != 'main' or not baseline.get('finalized'):
                raise ValueError('Baseline must be explicitly designated finalized main service')
            expected = (date.fromisoformat(packet['date'])-timedelta(days=7)).isoformat()
            if baseline.get('date') != expected and not baseline.get('exception_evidence'):
                raise ValueError('Baseline is stale; explicit exception required')
            content = Path(baseline['path']).read_bytes()
            if sha256(content).hexdigest() != baseline['sha256']:
                raise ValueError('Baseline hash mismatch')
            scratch = directory/'qa'
            scratch.mkdir()
            frozen = scratch/'baseline.idml'
            frozen.write_bytes(content)
        except (OSError, ValueError) as exc:
            result['issues'].append({'code': 'baseline_unavailable', 'message': str(exc)})
            frozen = None
    for service in packet['services']:
        service['date'] = packet['date']
        prefix = service['time'].replace(':', '')
        if frozen is not None:
            try:
                artifact = render_idml(frozen, service, layout, directory/f'{prefix}-bulletin.idml')
                artifact['service'] = service['key']
                result['artifacts'].append(artifact)
                result['issues'].append({'code': 'inherited_copy_unverified', 'service': service['key'],
                                         'message': 'Review inherited calendar, announcements, leaders, flowers and service-specific copy.'})
            except (OSError, ValueError) as exc:
                result['issues'].append({'code': 'bulletin_unavailable', 'service': service['key'], 'message': str(exc)})
        if service['key'] == 'main':
            try:
                artifacts = render_technical(service, cues, templates, directory)
                for artifact in artifacts:
                    artifact['service'] = 'main'
                result['artifacts'].extend(artifacts)
            except (OSError, ValueError) as exc:
                result['issues'].append({'code': 'technical_unavailable', 'service': 'main', 'message': str(exc)})
    (directory/'service-packet.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    text = ['# Draft packet review', '', 'Native composition and visual review are pending.', '']
    for artifact in result['artifacts']:
        text.append(f"- {Path(artifact['path']).name}: generated; proof pending.")
        if artifact.get('findings'):
            text.append(f"  Unconfirmed cues: {len(artifact['findings'])}.")
    for issue in result['issues']:
        text.append(f"- {issue.get('service', 'packet')}: {issue['code']} — {issue.get('message', '')}")
    Path(result['review_path']).write_text('\n'.join(text)+'\n', encoding='utf-8')
    temporary = directory/'manifest.tmp'
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(directory/'manifest.json')
    return result
