"""Replace labeled IDML stories while preserving all other package members."""

from hashlib import sha256
from pathlib import Path
import xml.etree.ElementTree as ET
from zipfile import ZipFile

LABELS = ('service_heading', 'worship_order')


def inspect_baseline(path):
    with ZipFile(path) as archive:
        names = archive.namelist()
        if len(names) != len(set(names)) or archive.testzip() is not None:
            raise ValueError('Invalid IDML ZIP members')
        mappings = {label: [] for label in LABELS}
        roots = {}
        for name in names:
            if name.endswith('.xml'):
                roots[name] = ET.fromstring(archive.read(name))
            if not name.startswith('Spreads/') or name not in roots:
                continue
            for frame in roots[name].iter('TextFrame'):
                for label in frame.findall('./Properties/Label/KeyValuePair'):
                    value = label.get('Value')
                    if label.get('Key') == 'Label' and value in mappings:
                        mappings[value].append(frame.get('ParentStory'))
        stories = {}
        for label, identifiers in mappings.items():
            if len(identifiers) != 1:
                raise ValueError(f'Missing or ambiguous label: {label}')
            matches = [name for name, root in roots.items() if name.startswith('Stories/')
                       and any(story.get('Self') == identifiers[0] for story in root.iter('Story'))]
            if len(matches) != 1:
                raise ValueError(f'Unresolved labeled story: {label}')
            stories[label] = matches[0]
        if len(set(stories.values())) != len(stories):
            raise ValueError('Distinct labels must resolve to distinct stories')
        styles = {style.get('Self') for root in roots.values() for style in root.iter('ParagraphStyle')}
        return {'stories': stories, 'styles': sorted(styles),
                'sha256': sha256(Path(path).read_bytes()).hexdigest()}


def render_idml(baseline, service, layout, target):
    target = Path(target)
    if target.exists():
        raise FileExistsError(target)
    info = inspect_baseline(baseline)
    allowed = set(layout['allowed_styles'])
    replacements = {}
    with ZipFile(baseline) as archive:
        for label, field in [('service_heading', 'heading_paragraphs'), ('worship_order', 'bulletin_paragraphs')]:
            name = info['stories'][label]
            root = ET.fromstring(archive.read(name))
            story = next(root.iter('Story'))
            old_paragraphs = list(story.findall('ParagraphStyleRange'))
            retained_styles = {'ParagraphStyle/' + style for style in
                               layout.get('retained_closing_styles', [])} if label == 'worship_order' else set()
            closing = []
            for paragraph in old_paragraphs:
                if paragraph.get('AppliedParagraphStyle') in retained_styles:
                    closing.append(paragraph)
                elif closing:
                    raise ValueError('Standing closing text must be a trailing paragraph block')
            for paragraph in old_paragraphs:
                story.remove(paragraph)
            for line in service[field]:
                style = line['style']
                ref = 'ParagraphStyle/' + style
                if style not in allowed or ref not in info['styles']:
                    raise ValueError(f'Unknown or unapproved paragraph style: {style}')
                # Use explicit styles; do not inherit arbitrary old per-entry overrides.
                paragraph = ET.SubElement(story, 'ParagraphStyleRange', AppliedParagraphStyle=ref)
                for part in line['text'].split('\n'):
                    run = ET.SubElement(paragraph, 'CharacterStyleRange', AppliedCharacterStyle='CharacterStyle/$ID/[No character style]')
                    ET.SubElement(run, 'Content').text = part
                    ET.SubElement(run, 'Br')
                if line.get('break_before'):
                    raise ValueError('Explicit panel break treatment requires a verified layout mapping')
            for paragraph in closing:
                story.append(paragraph)
            replacements[name] = ET.tostring(root, encoding='utf-8', xml_declaration=True)
        # Exclusive creation protects files the user may already be editing.
        with target.open('xb') as stream:
            with ZipFile(stream, 'w') as output:
                for member in archive.infolist():
                    output.writestr(member, replacements.get(member.filename, archive.read(member.filename)))
    return {'path': str(target), 'format': 'idml', 'sha256': sha256(target.read_bytes()).hexdigest(),
            'generation_status': 'generated', 'proof_status': 'pending',
            'changed_members': sorted(replacements)}
