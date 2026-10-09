"""Maintain one current document per service/role, preserving human edits."""

from datetime import date, timedelta
from hashlib import sha256
import json
import os
import shutil
from pathlib import Path
from tempfile import NamedTemporaryFile, TemporaryDirectory

from .bulletin import apply_bulletin_rules
from .idml import render_idml
from .model import validate_packet
from .technical import render_technical
from .proclaim import render_proclaim


def build_packet(packet, root, layout, cues, templates, *, phase="main"):
    """Main: prior-week baseline + four drafts. Early: finalized same-week baseline."""
    if phase not in {"main", "early"}:
        raise ValueError("Unknown preparation phase")
    packet = validate_packet(packet)
    apply_bulletin_rules(packet)
    state = Path(root)/'state/service_packets'
    state.mkdir(parents=True, exist_ok=True)
    lock = state/('build-'+packet['date']+'.lock')
    with lock.open('x', encoding='utf-8') as stream:
        stream.write(str(os.getpid()))
    try:
        with TemporaryDirectory(prefix='service-packet-') as scratch:
            return _build_packet(packet, root, layout, cues, templates, phase, Path(scratch))
    finally:
        lock.unlink()


def _file_identity(path):
    try:
        return sha256(Path(path).read_bytes()).hexdigest()
    except OSError:
        return 'unavailable'


def _build_packet(packet, root, layout, cues, templates, phase, directory):
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
    metadata = Path(root)/'state/service_packets/builds'/packet['date']/phase
    metadata.mkdir(parents=True, exist_ok=True)
    manifest_path = metadata/'manifest.json'
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
    previous = {}
    try:
        previous = json.loads(manifest_path.read_text(encoding='utf-8'))
    except FileNotFoundError:
        pass
    # A damaged ownership record must not grant permission to replace files.
    previous_artifacts = previous.get('artifacts', [])
    if (previous.get('build_identity') == identity and len(previous_artifacts) == expected_count
            and all(a.get('generation_status') == 'generated'
                    and _file_identity(a['path']) == a['sha256'] for a in previous_artifacts)):
        previous['reused'] = True
        return previous
    previous_by_name = {Path(a['path']).name: a for a in previous_artifacts}
    result = {'date': packet['date'], 'phase': phase, 'revision': 'current', 'artifacts': [],
              'build_identity': identity, 'reused': False,
              'issues': packet['issues'], 'review_path': str(metadata/'review.md'),
              'manifest_path': str(manifest_path), 'output_directory': str(parent)}
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
                if phase == 'early':
                    result['issues'].append({'code': 'inherited_personnel_manual_replacement',
                                             'service': service['key'],
                                             'message': 'Personnel are inherited from the main service and are NOT verified for this service. Replace the welcome team, worship leaders and technical team manually before publication; review other service-specific copy. Calendar and announcements retain the same-week finalized main content.'})
                else:
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
    published = []
    for artifact in result['artifacts']:
        staged = Path(artifact['path'])
        kind = artifact.get('kind', 'bulletin')
        target = parent/f"{artifact['service']}-{kind}.{artifact['format']}"
        old = previous_by_name.get(target.name, {})
        current_hash = _file_identity(target)
        generated_hash = old.get('generated_sha256')
        if target.exists() and (not generated_hash or current_hash != generated_hash):
            artifact = {**old, 'path': str(target), 'service': artifact['service'],
                        'kind': kind, 'format': artifact['format'], 'sha256': current_hash,
                        'generated_sha256': generated_hash,
                        'generation_status': 'preserved_user_edit', 'proof_status': 'pending'}
            result['issues'].append({'code': 'manual_edits_preserved',
                                     'service': artifact['service'],
                                     'message': f'{target.name}: existing edits preserved; reconcile source corrections in this file before delivery.'})
        else:
            # Recheck at publication, after rendering, so edits during the build survive.
            if _file_identity(target) != current_hash:
                raise RuntimeError(f'Output changed during publication: {target}')
            # The staging directory is temporary; no old generated revision is retained.
            # Write beside the target so replacement is atomic even across volumes.
            with NamedTemporaryFile(dir=parent, prefix='.publish-', delete=False) as stream:
                temporary = Path(stream.name)
                with staged.open('rb') as source:
                    shutil.copyfileobj(source, stream)
            try:
                if _file_identity(target) != current_hash:
                    raise RuntimeError(f'Output changed during publication: {target}')
                os.replace(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
            artifact.update(path=str(target), generated_sha256=artifact['sha256'])
        published.append(artifact)
    # Keep the last usable document when its replacement could not be rendered.
    names = {Path(a['path']).name for a in published}
    for old in previous_artifacts:
        path = Path(old['path'])
        if path.name not in names and path.is_file():
            published.append({**old, 'generation_status': 'previous_result_retained',
                              'sha256': _file_identity(path)})
            result['issues'].append({'code': 'previous_result_retained',
                                     'message': f'{path.name}: no replacement generated; review before use.'})
    result['artifacts'] = published
    (metadata/'service-packet.json').write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding='utf-8')
    text = ['# Draft packet review', '', 'Native composition and visual review are pending.', '']
    for artifact in result['artifacts']:
        text.append(f"- {Path(artifact['path']).name}: {artifact['generation_status']}; proof {artifact['proof_status']}.")
        if artifact.get('findings'):
            text.append(f"  Review findings: {len(artifact['findings'])}.")
    for issue in result['issues']:
        text.append(f"- {issue.get('service', 'packet')}: {issue['code']} — {issue.get('message', '')}")
    Path(result['review_path']).write_text('\n'.join(text)+'\n', encoding='utf-8')
    temporary = metadata/'manifest.tmp'
    temporary.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(manifest_path)
    return result
