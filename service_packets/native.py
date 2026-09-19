"""Explicitly initiated desktop export; not an unattended timeout/recovery worker."""

import json
import os
from pathlib import Path
import subprocess


def export_saved_indd(request):
    if request.get('format') != 'indd':
        raise ValueError('This adapter only exports saved INDD files')
    root = Path(request['input']).resolve().parent
    request_path = root/'export-request.json'
    with request_path.open('x', encoding='utf-8') as stream:
        json.dump(request, stream, indent=2)
    powershell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    script = Path(__file__).resolve().parents[1]/'tools/service_packets/proof.ps1'
    # PowerShell Core's module path can hide Windows PowerShell's built-in modules.
    environment = {key: value for key, value in os.environ.items()
                   if key.lower() != 'psmodulepath'}
    subprocess.run([str(powershell), '-NoProfile', '-File', str(script),
                    '-RequestPath', str(request_path), '-ApprovedRoot', str(root)],
                   check=True, capture_output=True, env=environment)
    return json.loads(Path(request['result']).read_text(encoding='utf-8-sig'))


def launch_desktop_job(request, approved_root):
    """Launch only the fixed worker; jobs.run_job owns validation and serialization."""
    root = Path(approved_root).resolve()
    request_path = root/(request['id']+'-request.json')
    with request_path.open('x', encoding='utf-8') as stream:
        json.dump(request, stream, indent=2)
    powershell = Path(os.environ['SystemRoot'])/'System32/WindowsPowerShell/v1.0/powershell.exe'
    worker = Path(__file__).resolve().parents[1]/'tools/service_packets/worker.ps1'
    environment = {key: value for key, value in os.environ.items() if key.lower() != 'psmodulepath'}
    with (root/(request['id']+'.log')).open('xb') as log:
        return subprocess.Popen([str(powershell), '-NoProfile', '-File', str(worker),
                                 '-RequestPath', str(request_path), '-ApprovedRoot', str(root)],
                                stdout=log, stderr=subprocess.STDOUT, env=environment,
                                creationflags=subprocess.CREATE_NO_WINDOW)
