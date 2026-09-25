"""Publish a new editable draft revision without touching prior handoffs."""

from datetime import date, timedelta
from hashlib import sha256
import json
import os
from pathlib import Path

from .idml import render_idml
from .model import validate_packet
from .technical import render_technical
from .proclaim import render_proclaim


def build_packet(packet, root, layout, cues, templates, *, phase="main"):
    """Main: prior-week baseline + four drafts. Early: finalized same-week baseline."""
    if phase not in {"main", "early"}:
        raise ValueError("Unknown preparation phase")
    packet = validate_packet(packet)
    state = Path(root)/'state/service_packets'
    state.mkdir(parents=True, exist_ok=True)
    lock = state/('build-'+packet['date']+'.lock')
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    try:
        return _build_packet(packet, root, layout, cues, templates, phase)
    finally:
        lock.unlink()


def _file_identity(path):
    try:
        return sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return 'unavailable'


def _build_packet(packet, root, layout, cues, templates, phase):
    selected = [s for s in packet["services"] if (s["key"] == "main") == (phase == "main")]
    if 'baseline' not in packet:
        pointer = Path(root)/'state/service_packets/baseline.json'
        try:
            packet['baseline'] = json.loads(pointer.read_text(encoding='utf-8'))
        except FileNotFoundError:
            packet['baseline'] = None
        except (OSError, ValueError) as exc:
            packet['baseline'] = None
            packet['issues'].append({'code': 'baseline_unavailable', 'message': str(exc)})
    parent = Path(root)/'outputs'/packet['date']
    parent.mkdir(parents=True, exist_ok=True)
    dependencies = {str(path): _file_identity(path) for path in templates.values()}
    for source in packet.get('sources', []):
        if source.get('path'):
            dependencies[source['path']] = _file_identity(source['path'])
    if packet.get('baseline'):
        dependencies[packet['baseline']['path']] = _file_identity(packet['baseline']['path'])
    code = {path.name: _file_identity(path) for path in Path(__file__).parent.glob('*.py')}
    identity = sha256(json.dumps({'packet': packet, 'layout': layout, 'cues': cues,
                                 'dependencies': dependencies, 'renderer': code, 'phase': phase},
                                sort_keys=True, ensure_ascii=False).encode('utf-8')).hexdigest()
    expected_count = len(selected) + (3 if any(s['key'] == 'main' for s in selected) else 0)
    for manifest in sorted(parent.glob('rev-*/manifest.json'), reverse=True):
        try:
            previous = json.loads(manifest.read_text(encoding='utf-8'))
            artifacts = previous['artifacts']
            if previous.get('build_identity') == identity:
                if (len(artifacts) == expected_count
                        and all(_file_identity(a['path']) == a['sha256'] for a in artifacts)):
                    previous['reused'] = True
                    return previous  # Proof state is retained, never upgraded by reuse.
                break  # Never fall back past a newer edited or incomplete handoff.
        except (OSError, ValueError, KeyError, TypeError):
            continue
    for number in range(1, 10000):
        directory = parent/f'rev-{number:03d}'
        try:
            directory.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise RuntimeError('Revision allocation exhausted')
    result = {'date': packet['date'], 'phase': phase, 'revision': directory.name, 'artifacts': [],
              'build_identity': identity, 'reused': False,
              'issues': packet['issues'], 'review_path': str(directory/'review.md')}
    if phase == 'main' and any(s['key'] != 'main' for s in packet['services']):
        result['issues'].append({'code': 'early_generation_deferred', 'message': 'Early bulletins await this Sunday\'s explicitly finalized main bulletin.'})
    baseline = packet.get('baseline')
    frozen = None
    if not baseline:
        result['issues'].append({'code': 'baseline_missing', 'message': 'Bulletins unavailable; supply eligible finalized main baseline.'})
    else:
        try:
            if baseline.get('service') != 'main' or not baseline.get('finalized'):
                raise ValueError('Baseline must be explicitly designated finalized main service')
            expected = packet['date'] if phase == 'early' else (date.fromisoformat(packet['date'])-timedelta(days=7)).isoformat()
            if phase == 'early' and baseline.get('date') != expected:
                raise ValueError('Early generation requires an explicitly finalized same-week main baseline')
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
    for service in selected:
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
                artifact = render_proclaim(service, packet, directory/f'{prefix}-proclaim.docx')
                artifact['service'] = 'main'
                result['artifacts'].append(artifact)
            except (OSError, ValueError) as exc:
                result['issues'].append({'code': 'proclaim_unavailable', 'service': 'main', 'message': str(exc)})
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
            text.append(f"  Review findings: {len(artifact['findings'])}.")
    for issue in result['issues']:
        text.append(f"- {issue.get('service', 'packet')}: {issue['code']} — {issue.get('message', '')}")
    Path(result['review_path']).write_text('\n'.join(text)+'\n', encoding='utf-8')
    temporary = directory/'manifest.tmp'
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(directory/'manifest.json')
    return result
