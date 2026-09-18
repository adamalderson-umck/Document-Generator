"""Local immutable source snapshots and structure-preserving DOCX inspection."""

from datetime import date, datetime, timezone
from hashlib import sha256
import json
from pathlib import Path
import re
from zipfile import ZipFile

from docx import Document
from docx.text.paragraph import Paragraph


def freeze_sources(root, date_string, candidates):
    if date.fromisoformat(date_string).isoformat() != date_string:
        raise ValueError('Invalid date')
    identifiers = set()
    for candidate in candidates:
        identifier = candidate.get('id', '')
        if (not re.fullmatch(r'[A-Za-z0-9_-]+', identifier)
                or identifier.upper() in {'CON', 'PRN', 'AUX', 'NUL'}
                or re.fullmatch(r'(COM|LPT)[0-9]', identifier.upper()) or identifier in identifiers):
            raise ValueError('Unsafe or duplicate source identifier')
        identifiers.add(identifier)
    parent = Path(root)/'inputs'/'service_packets'/date_string
    parent.mkdir(parents=True, exist_ok=True)
    for number in range(1, 10000):
        run = parent/f'run-{number:03d}'
        try:
            run.mkdir()
            break
        except FileExistsError:
            continue
    else:
        raise RuntimeError('Source run allocation exhausted')
    (run/'sources').mkdir()
    manifest = {'date': date_string, 'retrieved_at': datetime.now(timezone.utc).isoformat(), 'sources': []}
    for candidate in candidates:
        original = Path(candidate['path'])
        content = original.read_bytes()
        target = run/'sources'/(candidate['id'] + original.suffix)
        with target.open('xb') as stream:
            stream.write(content)
        manifest['sources'].append({**candidate, 'original_path': str(original),
                                    'path': target.relative_to(run).as_posix(),
                                    'sha256': sha256(content).hexdigest()})
    temporary = run/'source-manifest.tmp'
    temporary.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(run/'source-manifest.json')
    return run


def read_docx(path):
    document = Document(path)

    def blocks(container, prefix):
        output = []
        counters = {'p': 0, 'table': 0}
        for block in container.iter_inner_content():
            kind = 'p' if isinstance(block, Paragraph) else 'table'
            location = f'{prefix}/{kind}/{counters[kind]}'
            counters[kind] += 1
            if kind == 'p':
                output.append({'kind': 'paragraph', 'location': location, 'text': block.text,
                               'style': block.style.name,
                               'left_indent': block.paragraph_format.left_indent,
                               'first_line_indent': block.paragraph_format.first_line_indent,
                               'runs': [{'text': r.text, 'bold': r.bold, 'italic': r.italic,
                                         'underline': bool(r.underline)} for r in block.runs]})
            else:
                output.append({'kind': 'table', 'location': location, 'rows': [
                    [blocks(cell, f'{location}/row/{ri}/cell/{ci}') for ci, cell in enumerate(row.cells)]
                    for ri, row in enumerate(block.rows)]})
        return output
    with ZipFile(path) as archive:
        xml = archive.read('word/document.xml')
    warnings = ['source_structure_requires_visual_review'] if any(
        marker in xml for marker in [b'<w:ins ', b'<w:del ', b'<w:txbxContent', b'<w:footnoteReference']) else []
    return {'blocks': blocks(document, 'body'), 'warnings': warnings}
