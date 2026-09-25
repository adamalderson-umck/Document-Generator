"""Bounded isolated two-stage acceptance, callable by a scheduled agent.

Connector access must be independently exercised by the calling agent.
This program never finalizes files or starts native workers.
"""
import argparse
import copy
from datetime import datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import sys
from zipfile import ZipFile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from service_packets.build import build_packet
from service_packets.idml import inspect_baseline


def run(packet_path, baseline_path, runtime_path, output_root):
    read = lambda p: json.loads(Path(p).read_text(encoding='utf-8-sig'))
    packet, baseline, runtime = map(read, (packet_path, baseline_path, runtime_path))
    output_root = Path(output_root).resolve()
    output_root.mkdir(parents=True, exist_ok=False)
    inputs = {str(Path(p).resolve()): sha256(Path(p).read_bytes()).hexdigest()
              for p in (packet_path, baseline_path, runtime_path)}
    layout, cues = read(runtime['layout_path']), read(runtime['cues_path'])
    first = build_packet(packet, output_root, layout, cues, runtime['templates'], phase='main')
    early = copy.deepcopy(packet)
    early['baseline'] = baseline
    second = build_packet(early, output_root, layout, cues, runtime['templates'], phase='early')
    if len(first['artifacts']) != 4 or len(second['artifacts']) != 2:
        raise ValueError('Acceptance fixture did not produce four main and two early artifacts')
    allowed = set(inspect_baseline(baseline['path'])['stories'].values())
    for artifact in second['artifacts']:
        with ZipFile(baseline['path']) as source, ZipFile(artifact['path']) as target:
            for name in source.namelist():
                if name not in allowed and source.read(name) != target.read(name):
                    raise ValueError('Common baseline member changed: ' + name)
    for path, digest in inputs.items():
        if sha256(Path(path).read_bytes()).hexdigest() != digest:
            raise ValueError('Acceptance modified an input')
    result = {'status': 'passed', 'finished_at': datetime.now(timezone.utc).isoformat(),
              'main': first, 'early': second, 'input_hashes': inputs,
              'google_access': 'must_be_verified_by_calling_agent',
              'native_proof': 'separate_worker_validation'}
    (output_root/'acceptance.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--packet', required=True)
    parser.add_argument('--baseline', required=True)
    parser.add_argument('--runtime', required=True)
    parser.add_argument('--output', required=True)
    args = parser.parse_args()
    result = run(args.packet, args.baseline, args.runtime, args.output)
    print(json.dumps({'status': result['status'], 'report': str(Path(args.output)/'acceptance.json')}))
